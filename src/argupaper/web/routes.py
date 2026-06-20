"""FastAPI routes for the local ArguPaper workbench."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from argupaper.config import Config, load_config
from argupaper.memory.paper_store import PaperStore
from argupaper.web.jobs import AnalyzeJobRegistry
from argupaper.web.schemas import (
    AnalyzeJobStatusResponse,
    AnalyzeSubmitResponse,
    ConfigStatusResponse,
    PaperDetailResponse,
    PaperListResponse,
    SearchRequest,
    SearchResponse,
)
from argupaper.workflows import (
    AnalyzeOptions,
    AnalyzeWorkflow,
    ConfigurationError,
    ExternalServiceError,
    InputValidationError,
    SearchOptions,
)
from argupaper.workflows.search import InteractiveSearchWorkflow

router = APIRouter(prefix="/api", tags=["workbench"])
job_registry = AnalyzeJobRegistry()


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
    record = job_registry.create(upload_path, original_name, options)
    asyncio.create_task(_run_analyze_job(record.job_id, config))
    return AnalyzeSubmitResponse(job_id=record.job_id, status=record.status)


@router.get("/jobs/{job_id}", response_model=AnalyzeJobStatusResponse)
async def get_job(job_id: str) -> AnalyzeJobStatusResponse:
    """Return a background analyze job snapshot."""

    snapshot = job_registry.snapshot(job_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyze job not found.")
    return snapshot


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

    record = job_registry.get(job_id)
    if record is None:
        return

    job_registry.mark_running(job_id)

    def progress_callback(message: str) -> None:
        job_registry.add_progress(job_id, message)

    try:
        workflow = AnalyzeWorkflow(config)
        result = await workflow.run(record.options, progress_callback)
        job_registry.mark_succeeded(job_id, result)
    except Exception as exc:  # noqa: BLE001 - surfaced as job failure for local UI
        job_registry.mark_failed(job_id, exc)


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
