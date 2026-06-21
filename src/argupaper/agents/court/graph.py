"""Adversarial Paper Court LangGraph subgraph."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, StateGraph

from argupaper.agents.court.state import PaperCourtState
from argupaper.config import Config
from argupaper.domain.court import Argument, Claim, ClaimVerdict, CriticalClaimReport, Dispute, Evidence
from argupaper.domain.court.models import AttackTemplate, ClaimType, VerdictLabel
from argupaper.domain.paper.structured import StructuredExtractor
from argupaper.workflows.models import SearchOptions
from argupaper.workflows.search.workflow import SearchWorkflow

ProgressCallback = Callable[[str], None] | None

ATTACK_TEMPLATES: tuple[AttackTemplate, ...] = (
    "novelty_attack",
    "baseline_attack",
    "dataset_attack",
    "metric_attack",
    "ablation_attack",
    "causal_attack",
    "generalization_attack",
    "reproducibility_attack",
)


class PaperCourtGraph:
    """Coordinator for claim-level adversarial review sub-agents."""

    CLAIM_MARKERS = (
        "we propose",
        "we present",
        "we introduce",
        "we show",
        "we demonstrate",
        "we find",
        "our method",
        "our approach",
        "outperform",
        "state-of-the-art",
        "improve",
        "effective",
        "robust",
        "novel",
        "causal",
        "because",
        "generalize",
    )

    def __init__(
        self,
        config: Config,
        *,
        search_workflow_factory: Callable[[], SearchWorkflow] | None = None,
        progress_callback: ProgressCallback = None,
    ) -> None:
        self.config = config
        self.progress_callback = progress_callback
        self.extractor = StructuredExtractor()
        self.search_workflow_factory = search_workflow_factory or (lambda: SearchWorkflow(config))
        self.graph = self._build_graph()

    async def ainvoke(
        self,
        *,
        paper_id: str,
        title: str,
        markdown: str,
        max_rounds: int = 2,
    ) -> CriticalClaimReport:
        """Run the compiled paper court subgraph."""

        state: PaperCourtState = {
            "paper_id": paper_id,
            "title": title or "Untitled",
            "markdown": markdown,
            "max_rounds": max(1, max_rounds),
            "current_round": 0,
            "claims": [],
            "evidence": [],
            "challenges": [],
            "defenses": [],
            "disputes": [],
            "verdicts": [],
            "used_attack_keys": [],
            "new_challenge_count": 0,
            "stop_reason": "",
            "warnings": [],
            "report": None,
        }
        result = await self.graph.ainvoke(state)
        report = result.get("report")
        if isinstance(report, CriticalClaimReport):
            return report
        return self._build_report(result)

    def _build_graph(self) -> Any:
        graph = StateGraph(PaperCourtState)
        graph.add_node("ClaimExtractor", self._claim_extractor)
        graph.add_node("EvidenceBinder", self._evidence_binder)
        graph.add_node("Challenger", self._challenger)
        graph.add_node("Proposer", self._proposer)
        graph.add_node("Adjudicator", self._adjudicator)
        graph.add_node("ReportGenerator", self._report_generator)
        graph.set_entry_point("ClaimExtractor")
        graph.add_edge("ClaimExtractor", "EvidenceBinder")
        graph.add_edge("EvidenceBinder", "Challenger")
        graph.add_edge("Challenger", "Proposer")
        graph.add_edge("Proposer", "Adjudicator")
        graph.add_conditional_edges(
            "Adjudicator",
            self._route_after_adjudicator,
            {"challenge": "Challenger", "report": "ReportGenerator"},
        )
        graph.add_edge("ReportGenerator", END)
        return graph.compile()

    async def _claim_extractor(self, state: PaperCourtState) -> dict[str, Any]:
        self._progress("Court ClaimExtractor: extracting claim candidates...")
        markdown = state["markdown"]
        claims = self._extract_claims(markdown)
        warnings = list(state["warnings"])
        if not claims:
            warnings.append("ClaimExtractor found no strong claim markers; used the abstract/introduction fallback.")
            claims = self._fallback_claims(markdown)
        return {"claims": claims, "warnings": warnings}

    async def _evidence_binder(self, state: PaperCourtState) -> dict[str, Any]:
        self._progress("Court EvidenceBinder: binding paper chunks and related-work evidence...")
        chunks = self._chunk_markdown(state["paper_id"], state["markdown"])
        evidence: list[Evidence] = []
        warnings = list(state["warnings"])

        for claim in state["claims"]:
            evidence.extend(self._bind_local_evidence(claim, chunks))
            evidence.extend(self._bind_caption_evidence(claim, chunks))

        external = await self._search_external_related_work(state["claims"], warnings)
        evidence.extend(self._external_results_to_evidence(state["claims"], external))
        if not evidence:
            warnings.append("EvidenceBinder found no evidence chunks; downstream verdicts should be treated as unsupported.")
        return {"evidence": evidence, "warnings": warnings, "external_results": external}

    async def _challenger(self, state: PaperCourtState) -> dict[str, Any]:
        round_number = state["current_round"] + 1
        self._progress(f"Court Challenger: generating round {round_number} challenges...")
        used_attack_keys = list(state["used_attack_keys"])
        challenges = list(state["challenges"])
        disputes = list(state["disputes"])
        new_count = 0

        for claim in state["claims"]:
            claim_evidence = self._evidence_for_claim(state["evidence"], claim.claim_id)
            for template in self._templates_for_claim(claim, claim_evidence):
                attack_key = f"{claim.claim_id}:{template}"
                if attack_key in used_attack_keys:
                    continue
                used_attack_keys.append(attack_key)
                argument = Argument(
                    argument_id=f"challenge-{len(challenges) + 1}",
                    claim_id=claim.claim_id,
                    role="challenge",
                    template=template,
                    content=self._challenge_content(template, claim, claim_evidence),
                    evidence_ids=[item.evidence_id for item in claim_evidence[:4]],
                    round=round_number,
                )
                dispute = Dispute(
                    dispute_id=f"dispute-{len(disputes) + 1}",
                    claim_id=claim.claim_id,
                    round=round_number,
                    challenge=argument,
                )
                challenges.append(argument)
                disputes.append(dispute)
                new_count += 1
                if new_count >= max(1, len(state["claims"]) * 3):
                    break
            if new_count >= max(1, len(state["claims"]) * 3):
                break

        return {
            "current_round": round_number,
            "challenges": challenges,
            "disputes": disputes,
            "used_attack_keys": used_attack_keys,
            "new_challenge_count": new_count,
        }

    async def _proposer(self, state: PaperCourtState) -> dict[str, Any]:
        self._progress("Court Proposer: preparing evidence-grounded defenses...")
        defenses = list(state["defenses"])
        disputes = list(state["disputes"])
        for index, dispute in enumerate(disputes):
            if dispute.defense is not None or dispute.round != state["current_round"]:
                continue
            claim_evidence = self._evidence_for_claim(state["evidence"], dispute.claim_id)
            defense = Argument(
                argument_id=f"defense-{len(defenses) + 1}",
                claim_id=dispute.claim_id,
                role="defense",
                template=dispute.challenge.template,
                content=self._defense_content(dispute, claim_evidence),
                evidence_ids=[item.evidence_id for item in claim_evidence[:4]],
                round=dispute.round,
            )
            unresolved = self._unresolved_items(dispute, claim_evidence)
            disputes[index] = dispute.model_copy(
                update={
                    "defense": defense,
                    "unresolved_disputes": unresolved,
                    "resolved": not unresolved,
                }
            )
            defenses.append(defense)
        return {"defenses": defenses, "disputes": disputes}

    async def _adjudicator(self, state: PaperCourtState) -> dict[str, Any]:
        self._progress("Court Adjudicator: assigning claim verdicts...")
        verdicts = [
            self._adjudicate_claim(
                claim,
                self._evidence_for_claim(state["evidence"], claim.claim_id),
                [item for item in state["disputes"] if item.claim_id == claim.claim_id],
            )
            for claim in state["claims"]
        ]
        stop_reason = self._stop_reason(state, verdicts)
        return {"verdicts": verdicts, "stop_reason": stop_reason}

    async def _report_generator(self, state: PaperCourtState) -> dict[str, Any]:
        self._progress("Court ReportGenerator: assembling CriticalClaimReport...")
        return {"report": self._build_report(state)}

    def _route_after_adjudicator(self, state: PaperCourtState) -> str:
        return "report" if state.get("stop_reason") else "challenge"

    def _extract_claims(self, markdown: str) -> list[Claim]:
        scoped = "\n\n".join(
            section
            for section in (
                self.extractor._extract_section(markdown, ["abstract"]),
                self.extractor._extract_section(markdown, ["introduction", "overview"]),
                self.extractor._extract_section(markdown, ["conclusion", "discussion"]),
            )
            if section
        )
        haystack = scoped or markdown[:9000]
        sections = self._chunk_markdown("paper", haystack, max_chars=900)
        claims: list[Claim] = []
        for chunk in sections:
            for sentence in self._sentences(chunk["text"]):
                lowered = sentence.casefold()
                if self._looks_like_table_markup(sentence):
                    continue
                if len(sentence) < 30 or not any(marker in lowered for marker in self.CLAIM_MARKERS):
                    continue
                claim_id = f"claim-{len(claims) + 1}"
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        text=self._truncate(sentence, 320),
                        claim_type=self._classify_claim(sentence),
                        section=str(chunk["section"]),
                        page=None,
                        confidence=0.72,
                    )
                )
                if len(claims) >= 8:
                    return claims
        return claims

    def _fallback_claims(self, markdown: str) -> list[Claim]:
        abstract = self.extractor._extract_section(markdown, ["abstract"]) or markdown[:1500]
        sentences = self._sentences(abstract)
        claims: list[Claim] = []
        for sentence in sentences[:3]:
            if len(sentence) < 30:
                continue
            if self._looks_like_table_markup(sentence):
                continue
            claims.append(
                Claim(
                    claim_id=f"claim-{len(claims) + 1}",
                    text=self._truncate(sentence, 320),
                    claim_type=self._classify_claim(sentence),
                    section="abstract",
                    confidence=0.4,
                )
            )
        return claims

    def _chunk_markdown(
        self,
        paper_id: str,
        markdown: str,
        *,
        max_chars: int = 1100,
    ) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        section = "front_matter"
        buffer: list[str] = []
        index = 1

        def flush() -> None:
            nonlocal buffer, index
            text = "\n".join(buffer).strip()
            if not text:
                buffer = []
                return
            chunks.append(
                {
                    "chunk_id": f"{paper_id}:chunk:{index}",
                    "source": f"paper:{paper_id}",
                    "page": None,
                    "section": section,
                    "text": text,
                }
            )
            index += 1
            buffer = []

        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                flush()
                section = stripped.lstrip("#").strip() or "untitled"
                continue
            if not stripped:
                continue
            if sum(len(item) for item in buffer) + len(stripped) > max_chars:
                flush()
            buffer.append(stripped)
        flush()
        return chunks

    def _bind_local_evidence(self, claim: Claim, chunks: list[dict[str, Any]]) -> list[Evidence]:
        scored = []
        claim_tokens = self._tokens(claim.text)
        for chunk in chunks:
            chunk_tokens = self._tokens(str(chunk["text"]))
            overlap = claim_tokens & chunk_tokens
            if not overlap:
                continue
            score = len(overlap) / max(1, len(claim_tokens))
            if str(chunk["section"]).casefold() == claim.section.casefold():
                score += 0.15
            scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            Evidence(
                evidence_id=f"ev-{claim.claim_id}-{index}",
                claim_id=claim.claim_id,
                kind="paper_chunk",
                text=self._truncate(str(chunk["text"]), 700),
                chunk_id=str(chunk["chunk_id"]),
                source=str(chunk["source"]),
                page=chunk["page"],
                section=str(chunk["section"]),
                score=round(score, 3),
            )
            for index, (score, chunk) in enumerate(scored[:4], start=1)
        ]

    def _bind_caption_evidence(self, claim: Claim, chunks: list[dict[str, Any]]) -> list[Evidence]:
        claim_tokens = self._tokens(claim.text)
        evidence: list[Evidence] = []
        for chunk in chunks:
            text = str(chunk["text"])
            if not re.search(r"\b(?:figure|fig\.|table)\s*\d*", text, flags=re.I):
                continue
            overlap = claim_tokens & self._tokens(text)
            if not overlap:
                continue
            kind = "table_caption" if re.search(r"\btable\b", text, flags=re.I) else "figure_caption"
            evidence.append(
                Evidence(
                    evidence_id=f"caption-{claim.claim_id}-{len(evidence) + 1}",
                    claim_id=claim.claim_id,
                    kind=kind,
                    text=self._truncate(text, 500),
                    chunk_id=str(chunk["chunk_id"]),
                    source=str(chunk["source"]),
                    page=chunk["page"],
                    section=str(chunk["section"]),
                    score=round(len(overlap) / max(1, len(claim_tokens)), 3),
                )
            )
            if len(evidence) >= 2:
                break
        return evidence

    async def _search_external_related_work(
        self,
        claims: list[Claim],
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        query_parts = [claim.text for claim in claims[:2]]
        query = " ".join(query_parts)
        if not query:
            return []
        try:
            workflow = self.search_workflow_factory()
            result = await workflow.run(
                SearchOptions(
                    query=self._truncate(query, 300),
                    limit=5,
                    source="both",
                    interactive=False,
                    limit_overridden=True,
                    source_overridden=True,
                )
            )
        except Exception as exc:
            warnings.append(f"EvidenceBinder external related-work retrieval failed: {type(exc).__name__}: {exc}")
            return []
        warnings.extend(result.warnings)
        return [item.model_dump() for item in result.results]

    def _external_results_to_evidence(
        self,
        claims: list[Claim],
        results: list[dict[str, Any]],
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        for claim in claims:
            claim_tokens = self._tokens(claim.text)
            scored = []
            for result in results:
                text = " ".join(str(result.get(field, "")) for field in ("title", "abstract", "venue"))
                overlap = claim_tokens & self._tokens(text)
                score = len(overlap) / max(1, len(claim_tokens))
                if score > 0:
                    scored.append((score, result))
            scored.sort(key=lambda item: item[0], reverse=True)
            for index, (score, result) in enumerate(scored[:2], start=1):
                evidence.append(
                    Evidence(
                        evidence_id=f"external-{claim.claim_id}-{index}",
                        claim_id=claim.claim_id,
                        kind="external_paper",
                        text=self._truncate(str(result.get("abstract") or result.get("title", "")), 550),
                        chunk_id=f"external:{result.get('source', 'unknown')}:{index}",
                        source=str(result.get("source", "external")),
                        page=None,
                        section="external_related_work",
                        score=round(score, 3),
                        title=str(result.get("title", "")),
                        url=str(result.get("url", "")),
                    )
                )
        return evidence

    def _templates_for_claim(self, claim: Claim, evidence: list[Evidence]) -> list[AttackTemplate]:
        templates: list[AttackTemplate] = ["reproducibility_attack"]
        if claim.claim_type == "novelty":
            templates.append("novelty_attack")
        if claim.claim_type == "experiment":
            templates.extend(["baseline_attack", "dataset_attack", "metric_attack", "ablation_attack"])
        if claim.claim_type == "causal":
            templates.append("causal_attack")
        if claim.claim_type == "generalization":
            templates.extend(["generalization_attack", "dataset_attack"])
        if not any(item.kind == "external_paper" for item in evidence):
            templates.append("novelty_attack")
        return list(dict.fromkeys(templates))

    def _challenge_content(
        self,
        template: AttackTemplate,
        claim: Claim,
        evidence: list[Evidence],
    ) -> str:
        has_external = any(item.kind == "external_paper" for item in evidence)
        has_experiment = any(
            marker in " ".join(item.text for item in evidence).casefold()
            for marker in ("baseline", "dataset", "metric", "ablation", "accuracy", "f1")
        )
        content_by_template = {
            "novelty_attack": (
                "Novelty is not established unless related work evidence separates this claim from prior work."
                if not has_external
                else "External related work exists, but the claim still needs explicit differentiation from the closest prior papers."
            ),
            "baseline_attack": "Baseline strength is unclear; verify that comparisons cover strong and current baselines.",
            "dataset_attack": "Dataset coverage may be narrow or unspecified; check whether benchmark diversity supports the claim.",
            "metric_attack": "Metric choice may not measure the asserted outcome; check if reported metrics align with the claim wording.",
            "ablation_attack": "Ablation evidence is needed to isolate the contribution claimed by the method.",
            "causal_attack": "Causal wording requires intervention, counterfactual, or ablation evidence rather than correlation alone.",
            "generalization_attack": "Generalization beyond tested settings is risky without broader domain, model, or dataset coverage.",
            "reproducibility_attack": "Reproducibility is uncertain unless implementation details, data, and evaluation protocol are explicit.",
        }
        suffix = " Current evidence is thin." if not evidence or not has_experiment else ""
        return f"{content_by_template[template]} Claim: {claim.text}{suffix}"

    def _defense_content(self, dispute: Dispute, evidence: list[Evidence]) -> str:
        if not evidence:
            return (
                "No bound evidence supports a substantive defense. The claim should be downgraded to a weaker, "
                "explicitly scoped statement until direct evidence is added."
            )
        citations = ", ".join(item.evidence_id for item in evidence[:3])
        if any(item.kind == "paper_chunk" for item in evidence):
            return (
                f"Defense is limited to cited evidence ({citations}). The paper provides local textual support, "
                "but any wording beyond those chunks should be narrowed."
            )
        return (
            f"Defense is limited to related-work evidence ({citations}). This can contextualize the claim but "
            "does not directly prove the paper's asserted result."
        )

    def _unresolved_items(self, dispute: Dispute, evidence: list[Evidence]) -> list[str]:
        template = dispute.challenge.template
        text = " ".join(item.text for item in evidence).casefold()
        unresolved: list[str] = []
        if not evidence:
            unresolved.append("No direct evidence bound to this claim.")
        if template == "baseline_attack" and "baseline" not in text:
            unresolved.append("Strong baseline comparison remains unverified.")
        if template == "dataset_attack" and not re.search(r"\b(dataset|benchmark|corpus|evaluation)\b", text):
            unresolved.append("Dataset or benchmark coverage remains unclear.")
        if template == "metric_attack" and not re.search(r"\b(accuracy|f1|rouge|bleu|score|metric|auc|mrr|ndcg)\b", text):
            unresolved.append("Metric alignment remains unclear.")
        if template == "ablation_attack" and "ablation" not in text:
            unresolved.append("Ablation support remains missing.")
        if template == "causal_attack" and not re.search(r"\b(ablation|intervention|causal|because|effect)\b", text):
            unresolved.append("Causal identification remains unsupported.")
        if template == "novelty_attack" and not any(item.kind == "external_paper" for item in evidence):
            unresolved.append("External novelty validation remains missing.")
        return unresolved

    def _adjudicate_claim(
        self,
        claim: Claim,
        evidence: list[Evidence],
        disputes: list[Dispute],
    ) -> ClaimVerdict:
        unresolved = [item for dispute in disputes for item in dispute.unresolved_disputes]
        direct = [item for item in evidence if item.kind in {"paper_chunk", "figure_caption", "table_caption"}]
        external = [item for item in evidence if item.kind == "external_paper"]
        avg_score = sum(item.score for item in direct) / max(1, len(direct))

        verdict: VerdictLabel
        if not direct:
            verdict = "unsupported"
        elif claim.claim_type == "novelty" and not external:
            verdict = "needs_external_validation"
        elif len(unresolved) >= 3:
            verdict = "overclaimed"
        elif avg_score >= 0.28 and not unresolved:
            verdict = "supported"
        elif direct:
            verdict = "weakly_supported"
        else:
            verdict = "unsupported"

        risk = {
            "supported": "low",
            "weakly_supported": "medium",
            "needs_external_validation": "medium",
            "overclaimed": "high",
            "unsupported": "critical",
        }[verdict]
        return ClaimVerdict(
            claim_id=claim.claim_id,
            verdict=verdict,
            rationale=self._verdict_rationale(verdict, evidence, unresolved),
            risk_level=risk,  # type: ignore[arg-type]
            suggested_revision=self._suggested_revision(claim, verdict),
            required_check=self._required_check(claim, verdict, unresolved),
            converged=verdict in {"supported", "unsupported", "overclaimed"} or len(disputes) >= 2,
        )

    def _stop_reason(self, state: PaperCourtState, verdicts: list[ClaimVerdict]) -> str:
        if state["current_round"] >= state["max_rounds"]:
            return "max_rounds reached"
        if state["new_challenge_count"] == 0:
            return "no new challenges"
        if verdicts and all(item.converged for item in verdicts):
            return "adjudicator convergence"
        return ""

    def _build_report(self, state: PaperCourtState) -> CriticalClaimReport:
        return CriticalClaimReport(
            paper_id=state["paper_id"],
            title=state["title"],
            claims=state["claims"],
            evidence=state["evidence"],
            challenges=state["challenges"],
            defenses=state["defenses"],
            disputes=state["disputes"],
            verdicts=state["verdicts"],
            max_rounds=state["max_rounds"],
            rounds_completed=state["current_round"],
            stop_reason=state.get("stop_reason") or "report generated",
            warnings=state["warnings"],
        )

    def _verdict_rationale(
        self,
        verdict: VerdictLabel,
        evidence: list[Evidence],
        unresolved: list[str],
    ) -> str:
        if verdict == "supported":
            return "Direct paper evidence is aligned with the claim and no unresolved challenge remains."
        if verdict == "weakly_supported":
            return "Some direct evidence exists, but one or more challenge dimensions remain under-evidenced."
        if verdict == "needs_external_validation":
            return "The claim has local support but novelty or generality needs external related-work validation."
        if verdict == "overclaimed":
            return "The claim wording is stronger than the bound evidence because disputes remain unresolved."
        return "No direct paper evidence was bound to the claim."

    def _suggested_revision(self, claim: Claim, verdict: VerdictLabel) -> str:
        if verdict == "supported":
            return "Keep the claim, but cite the strongest bound evidence explicitly."
        if verdict == "weakly_supported":
            return f"Downgrade to a scoped claim: evidence suggests that {claim.text}"
        if verdict == "needs_external_validation":
            return "Retain only as a local contribution claim until closest related work is compared."
        if verdict == "overclaimed":
            return "Replace broad or causal wording with a narrower statement tied to observed evidence."
        return "Remove or rewrite as a hypothesis until supporting evidence is added."

    def _required_check(
        self,
        claim: Claim,
        verdict: VerdictLabel,
        unresolved: list[str],
    ) -> str:
        if unresolved:
            return "; ".join(unresolved[:3])
        if claim.claim_type == "experiment":
            return "Verify datasets, metrics, baselines, and ablations against the original tables."
        if claim.claim_type == "novelty":
            return "Compare against closest external related work."
        if verdict == "supported":
            return "Check that the report cites the bound chunk ids."
        return "Run manual evidence validation."

    def _classify_claim(self, text: str) -> ClaimType:
        lowered = text.casefold()
        if any(marker in lowered for marker in ("novel", "first", "new", "introduce")):
            return "novelty"
        if any(marker in lowered for marker in ("outperform", "improve", "accuracy", "score", "experiment", "result")):
            return "experiment"
        if any(marker in lowered for marker in ("cause", "because", "lead to", "effect", "thereby")):
            return "causal"
        if any(marker in lowered for marker in ("generalize", "across", "robust", "various", "diverse")):
            return "generalization"
        return "method"

    def _evidence_for_claim(self, evidence: list[Evidence], claim_id: str) -> list[Evidence]:
        return [item for item in evidence if item.claim_id == claim_id]

    def _sentences(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text)
        return [item.strip() for item in re.split(r"(?<=[.!?])\s+", normalized) if item.strip()]

    def _tokens(self, text: str) -> set[str]:
        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "our",
            "are",
            "was",
            "were",
            "into",
            "than",
            "then",
            "have",
            "has",
        }
        return {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.casefold())
            if token not in stopwords
        }

    def _looks_like_table_markup(self, text: str) -> bool:
        lowered = text.casefold()
        return any(marker in lowered for marker in ("<table", "<tr", "<td", "</td>", "</tr>", "</table>"))

    def _truncate(self, text: str, limit: int) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."

    def _progress(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)


def build_paper_court_graph(
    config: Config,
    *,
    progress_callback: ProgressCallback = None,
) -> PaperCourtGraph:
    """Build the default paper court subgraph wrapper."""

    return PaperCourtGraph(config, progress_callback=progress_callback)
