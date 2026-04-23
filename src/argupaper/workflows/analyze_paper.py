"""Workflow for CLI paper analysis."""

import asyncio
from pathlib import Path
from typing import Callable, Optional

from argupaper.chains.analysis import AnalysisChain
from argupaper.chains.debate import DebateChain
from argupaper.chains.evidence import EvidenceChain
from argupaper.agents.message import AgentMessage, DebateState
from argupaper.config import Config
from argupaper.extraction.structured import StructuredExtractor
from argupaper.judge.consensus import ConsensusDetector
from argupaper.memory.paper_store import PaperStore
from argupaper.output.report import ReportGenerator
from argupaper.pdf import MarkdownCache, MinerUClient, PDFPipeline
from argupaper.workflows.models import AnalyzeOptions, AnalyzeWorkflowResult, SearchOptions
from argupaper.workflows.search_papers import SearchWorkflow

ProgressCallback = Optional[Callable[[str], None]]
PipelineFactory = Optional[Callable[[], PDFPipeline]]


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
        pipeline_factory: PipelineFactory = None,
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
        self.pipeline_factory = pipeline_factory

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

        pipeline = self._build_pipeline()

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
        try:
            debate_state = await self.debate_chain.run(debate_context)
            if not debate_state.messages:
                warnings.append("Debate produced no messages; using fallback debate state.")
                debate_state = self._build_fallback_debate_state(debate_context)
        except Exception as exc:
            warnings.append(f"Debate failed: {exc}")
            debate_state = self._build_fallback_debate_state(debate_context)

        if progress_callback:
            progress_callback("Generating report...")
        debate_messages = [message.model_dump() for message in debate_state.messages]
        try:
            consensus = await self.consensus_detector.detect_consensus(
                debate_messages,
                analysis=analysis,
                evidence=evidence,
                supplementary_results=supplementary_results,
            )
        except Exception as exc:
            warnings.append(f"Judge failed while extracting consensus: {exc}")
            consensus = self._build_fallback_consensus(analysis, evidence, supplementary_results)

        try:
            confidence_score, conflict_intensity = await self.consensus_detector.compute_confidence(
                debate_messages,
                evidence=evidence,
                supplementary_results=supplementary_results,
            )
        except Exception as exc:
            warnings.append(f"Judge failed while computing confidence: {exc}")
            confidence_score, conflict_intensity = 50.0, "medium"

        report_payload = {
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
            "warnings": warnings,
        }
        try:
            report = await self.report_generator.generate(report_payload)
            report_markdown = self.report_generator.format_markdown(report)
        except Exception as exc:
            warnings.append(f"Report generation failed: {exc}")
            report_markdown = self._build_minimal_report(
                analysis=analysis,
                structured=structured,
                consensus=consensus,
                confidence_score=confidence_score,
                conflict_intensity=conflict_intensity,
                warnings=warnings,
            )

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

    def _build_pipeline(self) -> PDFPipeline:
        if self.pipeline_factory is not None:
            return self.pipeline_factory()

        mineru_client = MinerUClient(
            api_key=self.config.pdf.api_key,
            model_version="vlm",
        )
        cache = MarkdownCache(cache_dir=self.config.pdf.cache_dir)
        return PDFPipeline(
            mineru_client=mineru_client,
            cache=cache,
            public_url_base=self.config.pdf.public_url_base,
        )

    def _build_fallback_debate_state(self, debate_context: dict) -> DebateState:
        claims = [
            str(item).strip()
            for item in (
                debate_context.get("analysis", {}).get("key_claims")
                or [debate_context.get("analysis", {}).get("overview", "")]
            )
            if str(item).strip()
        ]
        support_content = "Fallback support position: the analysis pipeline retained a minimal positive case."
        skeptic_content = (
            "Fallback skeptic position: debate details were unavailable, so unresolved review risk remains."
        )
        evidence_refs = [
            *[
                str(item).strip()
                for item in debate_context.get("evidence", {}).get("datasets", [])
                if str(item).strip()
            ],
            *[
                str(item).strip()
                for item in debate_context.get("evidence", {}).get("metrics", [])
                if str(item).strip()
            ],
        ]
        return DebateState(
            round=1,
            current_claims=claims,
            consensus_reached=False,
            support_positions=[support_content],
            skeptic_positions=[skeptic_content],
            messages=[
                AgentMessage(
                    agent_role="support",
                    round=1,
                    content=support_content,
                    evidence_refs=evidence_refs,
                    claims_refs=claims,
                ),
                AgentMessage(
                    agent_role="skeptic",
                    round=1,
                    content=skeptic_content,
                    evidence_refs=evidence_refs,
                    claims_refs=claims,
                ),
            ],
        )

    def _build_fallback_consensus(
        self,
        analysis: dict,
        evidence: dict,
        supplementary_results: list[dict],
    ) -> dict[str, list[str]]:
        consensus_items: list[str] = []
        overview = str(analysis.get("overview", "")).strip()
        if overview:
            consensus_items.append(overview.rstrip(".") + ".")
        if supplementary_results:
            consensus_items.append("Supplementary retrieval returned related work for comparison.")

        disagreements: list[str] = []
        if not evidence.get("has_baseline"):
            disagreements.append("Baseline comparisons remain unclear.")
        if not evidence.get("has_ablation"):
            disagreements.append("Ablation evidence is missing or incomplete.")
        if not evidence.get("metrics"):
            disagreements.append("Evaluation metrics are not clearly stated.")
        if not disagreements:
            disagreements.append("Judge details were unavailable and require manual review.")

        supporting_evidence = [
            str(item).strip()
            for item in [
                *evidence.get("datasets", []),
                *evidence.get("metrics", []),
            ]
            if str(item).strip()
        ]
        return {
            "consensus": consensus_items,
            "disagreements": disagreements,
            "supporting_evidence": list(dict.fromkeys(supporting_evidence)),
        }

    def _build_minimal_report(
        self,
        *,
        analysis: dict,
        structured: dict,
        consensus: dict[str, list[str]],
        confidence_score: float,
        conflict_intensity: str,
        warnings: list[str],
    ) -> str:
        overview = analysis.get("overview") or structured.get("problem") or "No overview available."
        consensus_lines = "\n".join(f"- {item}" for item in consensus.get("consensus", [])) or "- None"
        disagreement_lines = (
            "\n".join(f"- {item}" for item in consensus.get("disagreements", [])) or "- None"
        )
        warning_lines = "\n".join(f"- {item}" for item in warnings) or "- None"
        return f"""# Research Overview

{overview}

## Warnings

{warning_lines}

## Consensus vs Disagreement

### Consensus

{consensus_lines}

### Disagreement

{disagreement_lines}

## Confidence Score

- Confidence: {confidence_score:.2f}
- Conflict intensity: {conflict_intensity}
"""
