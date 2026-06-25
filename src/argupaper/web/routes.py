"""FastAPI routes for the local ArguPaper workbench."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from argupaper.agents.chat import ChatAgentRuntime
from argupaper.cli.commands.common import resolve_auto_report_path
from argupaper.config import Config, load_config
from argupaper.memory.paper_store import PaperStore
from argupaper.web.jobs import AnalyzeJobRegistry, WorkflowJobRegistry
from argupaper.web.schemas import (
    AnalyzeJobStatusResponse,
    AnalyzeSubmitResponse,
    ChatSessionResponse,
    ChatTurnRequest,
    ChatTurnResponse,
    ConfigStatusResponse,
    ConvertPathRequest,
    CourtRequest,
    DebateRequest,
    PaperDetailResponse,
    PaperListResponse,
    RAGDeleteRequest,
    RAGIndexRequest,
    RAGSearchRequest,
    SearchRequest,
    SearchResponse,
    WorkflowJobStatusResponse,
    WorkflowSubmitResponse,
)
from argupaper.workflows import (
    AnalyzeOptions,
    AnalyzeWorkflow,
    ConfigurationError,
    ConvertOptions,
    ConvertWorkflow,
    CourtOptions,
    CourtWorkflow,
    ExternalServiceError,
    InputValidationError,
    RAGDeleteOptions,
    RAGIndexOptions,
    RAGSearchOptions,
    RAGWorkflow,
    SearchOptions,
)
from argupaper.workflows.search import InteractiveSearchWorkflow

router = APIRouter(prefix="/api", tags=["workbench"])
analyze_job_registry = AnalyzeJobRegistry()
workflow_job_registry = WorkflowJobRegistry()
chat_sessions: dict[str, ChatAgentRuntime] = {}


@router.post("/search", response_model=SearchResponse)
async def search_papers(request: SearchRequest) -> SearchResponse:
    """Run the existing search workflow and return JSON."""

    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Search query is required.")

    try:
        config = load_config(require_pdf_api_key=False)
        workflow = InteractiveSearchWorkflow(config)
        result = await workflow.run(
            SearchOptions(
                query=query,
                limit=request.limit,
                source=request.source,
                verbose=request.verbose,
                raw_request=query,
                requested_limit=request.limit,
                interactive=False,
                limit_overridden=True,
                source_overridden=True,
            )
        )
        return SearchResponse(result=result)
    except InputValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, exc) from exc
    except ExternalServiceError as exc:
        raise _http_error(status.HTTP_502_BAD_GATEWAY, exc) from exc
    except ConfigurationError as exc:
        raise _http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, exc) from exc


@router.post("/analyze", response_model=AnalyzeSubmitResponse)
async def submit_analyze_job(
    file: UploadFile = File(...),
    rounds: int = Form(default=3),
    force_reconvert: bool = Form(default=False),
    verbose: bool = Form(default=False),
) -> AnalyzeSubmitResponse:
    """Upload a PDF and start an analysis job."""

    if rounds <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rounds must be greater than 0.")

    original_name = Path(file.filename or "paper.pdf").name
    if Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .pdf uploads are supported.")

    try:
        config = load_config(require_pdf_api_key=True)
    except ConfigurationError as exc:
        raise _http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, exc) from exc

    upload_path = await _save_upload(file, config, original_name)
    options = AnalyzeOptions(
        paper_path=upload_path,
        rounds=rounds,
        force_reconvert=force_reconvert,
        verbose=verbose,
    )
    record = analyze_job_registry.create(upload_path, original_name, options)
    asyncio.create_task(_run_analyze_job(record.job_id, config))
    return AnalyzeSubmitResponse(job_id=record.job_id, status=record.status)


@router.get("/jobs/{job_id}", response_model=AnalyzeJobStatusResponse)
async def get_job(job_id: str) -> AnalyzeJobStatusResponse:
    """Return a background analyze job snapshot."""

    snapshot = analyze_job_registry.snapshot(job_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyze job not found.")
    return snapshot


@router.get("/workflow-jobs/{job_id}", response_model=WorkflowJobStatusResponse)
async def get_workflow_job(job_id: str) -> WorkflowJobStatusResponse:
    """Return a generic workflow job snapshot."""

    snapshot = workflow_job_registry.snapshot(job_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow job not found.")
    return snapshot


@router.post("/convert/upload", response_model=WorkflowSubmitResponse)
async def submit_convert_upload(
    file: UploadFile = File(...),
    output_path: str | None = Form(default=None),
    force: bool = Form(default=False),
) -> WorkflowSubmitResponse:
    """Upload a PDF and start a conversion job."""

    original_name = Path(file.filename or "paper.pdf").name
    if Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .pdf uploads are supported.")

    try:
        config = load_config(require_pdf_api_key=True)
    except ConfigurationError as exc:
        raise _http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, exc) from exc

    upload_path = await _save_upload(file, config, original_name)
    options = ConvertOptions(
        pdf_path=upload_path,
        output_path=Path(output_path) if output_path else None,
        force_reconvert=force,
    )
    record = workflow_job_registry.create("convert", original_name)
    asyncio.create_task(_run_convert_job(record.job_id, config, options))
    return WorkflowSubmitResponse(job_id=record.job_id, status=record.status)


@router.post("/convert/path", response_model=WorkflowSubmitResponse)
async def submit_convert_path(request: ConvertPathRequest) -> WorkflowSubmitResponse:
    """Start a conversion job for a local PDF path or folder path."""

    if bool(request.pdf_path) == bool(request.folder_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of pdf_path or folder_path.",
        )
    try:
        config = load_config(require_pdf_api_key=True)
    except ConfigurationError as exc:
        raise _http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, exc) from exc

    label = request.pdf_path or request.folder_path or "convert"
    options = ConvertOptions(
        pdf_path=Path(request.pdf_path) if request.pdf_path else None,
        folder_path=Path(request.folder_path) if request.folder_path else None,
        output_path=Path(request.output_path) if request.output_path else None,
        force_reconvert=request.force,
    )
    record = workflow_job_registry.create("convert", label)
    asyncio.create_task(_run_convert_job(record.job_id, config, options))
    return WorkflowSubmitResponse(job_id=record.job_id, status=record.status)


@router.post("/debate", response_model=WorkflowSubmitResponse)
async def submit_debate(request: DebateRequest) -> WorkflowSubmitResponse:
    """Start a debate analysis job for a saved paper name or local PDF path."""

    paper = request.paper.strip()
    if paper.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL debate analysis is not supported.")

    output_path = Path(request.output_path) if request.output_path else None
    if output_path is None and request.save_report:
        output_path = resolve_auto_report_path(Path(paper))

    paper_path = Path(paper)
    if paper_path.exists():
        if paper_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Input must be a .pdf file.")
        options = AnalyzeOptions(
            paper_path=paper_path,
            output_path=output_path,
            rounds=request.rounds,
            force_reconvert=request.force,
            verbose=request.verbose,
        )
    else:
        options = AnalyzeOptions(
            paper_name=paper,
            output_path=output_path,
            rounds=request.rounds,
            force_reconvert=request.force,
            verbose=request.verbose,
        )

    config = load_config(require_pdf_api_key=False)
    record = workflow_job_registry.create("debate", paper)
    asyncio.create_task(_run_debate_job(record.job_id, config, options))
    return WorkflowSubmitResponse(job_id=record.job_id, status=record.status)


@router.post("/court", response_model=WorkflowSubmitResponse)
async def submit_court(request: CourtRequest) -> WorkflowSubmitResponse:
    """Start a claim-level paper court job."""

    config = load_config(require_pdf_api_key=False)
    options = CourtOptions(
        paper_id=request.paper_id,
        output_path=Path(request.output_path) if request.output_path else None,
        max_rounds=request.rounds,
        verbose=request.verbose,
    )
    record = workflow_job_registry.create("court", request.paper_id)
    asyncio.create_task(_run_court_job(record.job_id, config, options))
    return WorkflowSubmitResponse(job_id=record.job_id, status=record.status)


@router.get("/rag/status")
async def get_rag_status() -> object:
    """Return local RAG configuration."""

    workflow = RAGWorkflow(load_config(require_pdf_api_key=False))
    try:
        return workflow.status()
    finally:
        await workflow.close()


@router.post("/rag/index", response_model=WorkflowSubmitResponse)
async def submit_rag_index(request: RAGIndexRequest) -> WorkflowSubmitResponse:
    """Start a RAG indexing job."""

    config = load_config(require_pdf_api_key=False)
    record = workflow_job_registry.create("rag-index", request.paper_id)
    asyncio.create_task(
        _run_rag_index_job(record.job_id, config, RAGIndexOptions(paper_id=request.paper_id, dry_run=request.dry_run))
    )
    return WorkflowSubmitResponse(job_id=record.job_id, status=record.status)


@router.post("/rag/delete", response_model=WorkflowSubmitResponse)
async def submit_rag_delete(request: RAGDeleteRequest) -> WorkflowSubmitResponse:
    """Start a RAG delete job."""

    config = load_config(require_pdf_api_key=False)
    record = workflow_job_registry.create("rag-delete", request.paper_id)
    asyncio.create_task(_run_rag_delete_job(record.job_id, config, RAGDeleteOptions(paper_id=request.paper_id)))
    return WorkflowSubmitResponse(job_id=record.job_id, status=record.status)


@router.post("/rag/search")
async def search_rag(request: RAGSearchRequest) -> object:
    """Search local RAG chunks."""

    workflow = RAGWorkflow(load_config(require_pdf_api_key=False))
    try:
        return await workflow.search(
            RAGSearchOptions(
                content=request.content,
                paper_id=request.paper_id,
                top_k=request.top_k,
                section_type=request.section_type,
                score_threshold=request.score_threshold,
                context_max_chars=request.context_max_chars,
            )
        )
    except InputValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, exc) from exc
    finally:
        await workflow.close()


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session() -> ChatSessionResponse:
    """Create a stateful chat agent session."""

    session_id = uuid4().hex
    config = load_config(require_pdf_api_key=False)
    chat_sessions[session_id] = ChatAgentRuntime(config)
    return ChatSessionResponse(session_id=session_id)


@router.post("/chat/sessions/{session_id}/turn", response_model=ChatTurnResponse)
async def run_chat_turn(session_id: str, request: ChatTurnRequest) -> ChatTurnResponse:
    """Run one chat agent turn in an existing session."""

    runtime = chat_sessions.get(session_id)
    if runtime is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    result = await runtime.run_turn(request.message.strip())
    return ChatTurnResponse(
        response=result.response,
        interrupted=result.interrupted,
        warnings=result.warnings,
        selected_paper=result.selected_paper,
        log_path=result.log_path,
    )


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    query: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> PaperListResponse:
    """List or search saved paper records."""

    store = _build_paper_store()
    records = await store.search_papers(query) if query else await store.list_papers()
    return PaperListResponse(records=records[:limit])


@router.get("/papers/{paper_id}", response_model=PaperDetailResponse)
async def get_paper(paper_id: str) -> PaperDetailResponse:
    """Return one saved paper record by id or unique prefix."""

    store = _build_paper_store()
    record = await store.get_paper(paper_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved paper record not found.")
    return PaperDetailResponse(
        metadata=record.get("metadata", {}),
        abstract=record.get("abstract", {}),
        report=str(record.get("report", "")),
        markdown=str(record.get("markdown", "")),
    )


@router.get("/config/status", response_model=ConfigStatusResponse)
async def get_config_status() -> ConfigStatusResponse:
    """Return non-secret configuration status for the local UI."""

    config = load_config(require_pdf_api_key=False)
    return ConfigStatusResponse(
        mineru_api_configured=bool(config.pdf.api_key),
        semantic_scholar_configured=bool(config.retrieval.semantic_scholar_api_key),
        serpapi_configured=bool(config.retrieval.serpapi_api_key),
        paper_storage_path=config.paper_storage_path,
        cache_path=config.pdf.cache_dir,
        log_path=config.log.root_path,
        search_log_path=config.log.search_path,
        convert_log_path=config.log.convert_path,
        web_log_path=config.log.web_path,
        rag_log_path=config.log.rag_path,
        analyze_retrieval_loop_enabled=config.analyze_enable_retrieval_loop,
    )


async def _save_upload(file: UploadFile, config: Config, original_name: str) -> Path:
    """Save an uploaded PDF into the local data directory."""

    upload_dir = Path(config.data_path) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / f"{Path(original_name).stem}-{uuid4().hex[:12]}.pdf"

    with upload_path.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    await file.close()
    return upload_path


async def _run_analyze_job(job_id: str, config: Config) -> None:
    """Execute an analyze workflow and update job state."""

    record = analyze_job_registry.get(job_id)
    if record is None:
        return

    analyze_job_registry.mark_running(job_id)

    def progress_callback(message: str) -> None:
        analyze_job_registry.add_progress(job_id, message)

    try:
        workflow = AnalyzeWorkflow(config)
        result = await workflow.run(record.options, progress_callback)
        analyze_job_registry.mark_succeeded(job_id, result)
    except Exception as exc:  # noqa: BLE001 - surfaced as job failure for local UI
        analyze_job_registry.mark_failed(job_id, exc)


async def _run_convert_job(job_id: str, config: Config, options: ConvertOptions) -> None:
    workflow_job_registry.mark_running(job_id)

    def progress_callback(message: str) -> None:
        workflow_job_registry.add_progress(job_id, message)

    def file_event_callback(message: str) -> None:
        workflow_job_registry.add_progress(job_id, message)

    try:
        result = await ConvertWorkflow(config).run(options, progress_callback, file_event_callback)
        workflow_job_registry.mark_succeeded(job_id, result)
    except Exception as exc:  # noqa: BLE001 - surfaced as job failure for local UI
        workflow_job_registry.mark_failed(job_id, exc)


async def _run_debate_job(job_id: str, config: Config, options: AnalyzeOptions) -> None:
    workflow_job_registry.mark_running(job_id)

    def progress_callback(message: str) -> None:
        workflow_job_registry.add_progress(job_id, message)

    try:
        result = await AnalyzeWorkflow(config).run(options, progress_callback)
        workflow_job_registry.mark_succeeded(job_id, result, result.warnings)
    except Exception as exc:  # noqa: BLE001 - surfaced as job failure for local UI
        workflow_job_registry.mark_failed(job_id, exc)


async def _run_court_job(job_id: str, config: Config, options: CourtOptions) -> None:
    workflow_job_registry.mark_running(job_id)

    def progress_callback(message: str) -> None:
        workflow_job_registry.add_progress(job_id, message)

    try:
        result = await CourtWorkflow(config).run(options, progress_callback)
        workflow_job_registry.mark_succeeded(job_id, result, result.warnings)
    except Exception as exc:  # noqa: BLE001 - surfaced as job failure for local UI
        workflow_job_registry.mark_failed(job_id, exc)


async def _run_rag_index_job(job_id: str, config: Config, options: RAGIndexOptions) -> None:
    workflow_job_registry.mark_running(job_id)
    workflow = RAGWorkflow(config)

    def progress_callback(message: str) -> None:
        workflow_job_registry.add_progress(job_id, message)

    try:
        result = await workflow.index_paper(options, progress_callback)
        workflow_job_registry.mark_succeeded(job_id, result, result.warnings)
    except Exception as exc:  # noqa: BLE001 - surfaced as job failure for local UI
        workflow_job_registry.mark_failed(job_id, exc)
    finally:
        await workflow.close()


async def _run_rag_delete_job(job_id: str, config: Config, options: RAGDeleteOptions) -> None:
    workflow_job_registry.mark_running(job_id)
    workflow = RAGWorkflow(config)

    def progress_callback(message: str) -> None:
        workflow_job_registry.add_progress(job_id, message)

    try:
        result = await workflow.delete_paper(options, progress_callback)
        workflow_job_registry.mark_succeeded(job_id, result, result.warnings)
    except Exception as exc:  # noqa: BLE001 - surfaced as job failure for local UI
        workflow_job_registry.mark_failed(job_id, exc)
    finally:
        await workflow.close()


def _build_paper_store() -> PaperStore:
    """Build PaperStore from the current non-secret config."""

    config = load_config(require_pdf_api_key=False)
    return PaperStore(storage_path=config.paper_storage_path)


def _http_error(status_code: int, exc: Exception) -> HTTPException:
    """Map a workflow exception to a readable HTTP error."""

    return HTTPException(
        status_code=status_code,
        detail=f"{type(exc).__name__}: {exc}",
    )
