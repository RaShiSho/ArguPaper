"""Workflow for CLI paper analysis."""

import asyncio
from pathlib import Path
from typing import Callable, Optional

from argupaper.chains.analysis import AnalysisChain
from argupaper.chains.debate import DebateChain
from argupaper.chains.evidence import EvidenceChain
from argupaper.config import Config
from argupaper.extraction.structured import StructuredExtractor
from argupaper.judge.consensus import ConsensusDetector
from argupaper.memory.paper_store import PaperStore
from argupaper.output.report import ReportGenerator
from argupaper.pdf import MarkdownCache, MinerUClient, PDFPipeline
from argupaper.workflows.models import AnalyzeOptions, AnalyzeWorkflowResult, SearchOptions
from argupaper.workflows.search_papers import SearchWorkflow

ProgressCallback = Optional[Callable[[str], None]]


class AnalyzeWorkflow:
    """Orchestrates PDF processing and report generation for the CLI."""

    def __init__(
        self,
        config: Config,
        extractor: Optional[StructuredExtractor] = None,
        analysis_chain: Optional[AnalysisChain] = None,
        evidence_chain: Optional[EvidenceChain] = None,
        debate_chain: Optional[DebateChain] = None,
        consensus_detector: Optional[ConsensusDetector] = None,
        report_generator: Optional[ReportGenerator] = None,
        paper_store: Optional[PaperStore] = None,
        search_workflow: Optional[SearchWorkflow] = None,
    ):
        self.config = config
        self.extractor = extractor or StructuredExtractor()
        self.analysis_chain = analysis_chain or AnalysisChain()
        self.evidence_chain = evidence_chain or EvidenceChain()
        self.debate_chain = debate_chain or DebateChain(max_rounds=config.debate.max_rounds)
        self.consensus_detector = consensus_detector or ConsensusDetector()
        self.report_generator = report_generator or ReportGenerator()
        self.paper_store = paper_store or PaperStore(storage_path=Path(config.data_path) / "papers")
        self.search_workflow = search_workflow or SearchWorkflow(config)

    async def run(
        self,
        options: AnalyzeOptions,
        progress_callback: ProgressCallback = None,
    ) -> AnalyzeWorkflowResult:
        """Run the analysis workflow."""

        paper_path = Path(options.paper_path)
        self.debate_chain.max_rounds = options.rounds
        if progress_callback:
            progress_callback("Converting PDF to Markdown...")

        mineru_client = MinerUClient(
            api_key=self.config.pdf.api_key,
            model_version="vlm",
        )
        cache = MarkdownCache(cache_dir=self.config.pdf.cache_dir)
        pipeline = PDFPipeline(
            mineru_client=mineru_client,
            cache=cache,
            public_url_base=self.config.pdf.public_url_base,
        )

        warnings: list[str] = []
        try:
            result = await pipeline.process(paper_path, force_reconvert=options.force_reconvert)
        finally:
            await pipeline.close()

        markdown = result.markdown or ""
        paper_id = result.cache_key

        if progress_callback:
            progress_callback("Extracting structure...")
        structured = await self.extractor.extract_abstract(markdown)
        method_info = await self.extractor.extract_method(markdown)
        experiments = await self.extractor.extract_experiments(markdown)

        if progress_callback:
            progress_callback("Running analysis...")
        analysis = await self.analysis_chain.run(markdown)

        if progress_callback:
            progress_callback("Running evidence checks...")
        evidence = await self.evidence_chain.run(markdown)

        supplementary_search_used = False
        supplementary_results: list[dict] = []
        if self.config.analyze_enable_retrieval_loop and evidence.get("needs_supplementary_search"):
            if progress_callback:
                progress_callback("Running supplementary retrieval...")
            try:
                query = analysis.get("title") or structured.get("problem") or paper_path.stem
                search_result = await self.search_workflow.run(
                    SearchOptions(query=query, limit=3, source="semantic_scholar", verbose=False)
                )
                supplementary_results = [item.model_dump() for item in search_result.results]
                supplementary_search_used = len(supplementary_results) > 0
                warnings.extend(search_result.warnings)
            except Exception as exc:
                warnings.append(f"Supplementary retrieval failed: {exc}")

        if progress_callback:
            progress_callback("Running debate...")
        debate_context = {
            "analysis": analysis,
            "evidence": evidence,
            "structured": structured,
            "method": method_info,
            "experiments": experiments,
            "supplementary_results": supplementary_results,
        }
        debate_state = await self.debate_chain.run(debate_context)

        if progress_callback:
            progress_callback("Generating report...")
        consensus = await self.consensus_detector.detect_consensus(
            [message.model_dump() for message in debate_state.messages]
        )
        confidence_score, conflict_intensity = await self.consensus_detector.compute_confidence(
            support_score=float(len(debate_state.support_positions)),
            oppose_score=float(len(debate_state.skeptic_positions)),
        )

        report = await self.report_generator.generate(
            {
                "analysis": analysis,
                "structured": structured,
                "method": method_info,
                "experiments": experiments,
                "evidence": evidence,
                "supplementary_results": supplementary_results,
                "debate": debate_state,
                "consensus": consensus,
                "confidence_score": confidence_score,
                "conflict_intensity": conflict_intensity,
            }
        )
        report_markdown = self.report_generator.format_markdown(report)

        await self.paper_store.save_paper(
            paper_id,
            {
                "metadata": {
                    "paper_id": paper_id,
                    "source": str(paper_path),
                    "title": analysis.get("title") or paper_path.stem,
                    "from_cache": result.from_cache,
                },
                "abstract": structured,
                "markdown": markdown,
                "report": report_markdown,
            },
        )

        return AnalyzeWorkflowResult(
            report_markdown=report_markdown,
            report_title=analysis.get("title") or paper_path.stem,
            from_cache=result.from_cache,
            paper_id=paper_id,
            supplementary_search_used=supplementary_search_used,
            warnings=warnings,
        )

    def run_sync(
        self,
        options: AnalyzeOptions,
        progress_callback: ProgressCallback = None,
    ) -> AnalyzeWorkflowResult:
        """Synchronous wrapper used by Typer commands."""

        return asyncio.run(self.run(options, progress_callback))
