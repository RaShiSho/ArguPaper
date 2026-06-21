"""Consensus detection and confidence scoring."""

from typing import Literal


class ConsensusDetector:
    """Detects consensus and disagreements from debate results."""

    async def detect_consensus(
        self,
        debate_messages: list[dict],
        analysis: dict | None = None,
        evidence: dict | None = None,
        supplementary_results: list[dict] | None = None,
    ) -> dict[str, list[str]]:
        """Detect consensus points from debate and evidence signals."""

        analysis = analysis or {}
        evidence = evidence or {}
        supplementary_results = supplementary_results or []

        support_messages = [msg for msg in debate_messages if msg.get("agent_role") == "support"]
        skeptic_messages = [msg for msg in debate_messages if msg.get("agent_role") == "skeptic"]

        consensus: list[str] = []
        research_problem = self._clean_sentence(
            analysis.get("research_problem") or analysis.get("overview") or ""
        )
        technical_route = self._clean_sentence(
            analysis.get("technical_route") or analysis.get("method_analysis") or ""
        )
        datasets = [str(item).strip() for item in evidence.get("datasets", []) if str(item).strip()]
        metrics = [str(item).strip() for item in evidence.get("metrics", []) if str(item).strip()]

        if research_problem:
            consensus.append(f"The paper studies {research_problem}.")
        if technical_route:
            consensus.append(f"The main technical approach is {technical_route}.")
        if datasets or metrics:
            coverage_parts: list[str] = []
            if datasets:
                coverage_parts.append(f"evaluated on {', '.join(datasets[:3])}")
            if metrics:
                coverage_parts.append(f"reported with {', '.join(metrics[:3])}")
            consensus.append(f"The available evidence is {' and '.join(coverage_parts)}.")
        if supplementary_results:
            consensus.append("Supplementary retrieval provides related work for method comparison.")

        disagreements: list[str] = []
        if not evidence.get("has_baseline"):
            disagreements.append("Baseline comparisons remain unclear.")
        if not evidence.get("has_ablation"):
            disagreements.append("Ablation evidence is missing or incomplete.")
        if not metrics:
            disagreements.append("Evaluation metrics are not clearly stated.")

        unsupported_claims = [
            str(item).strip()
            for item in evidence.get("unsupported_claims", [])
            if str(item).strip()
        ]
        contradictions = [
            str(item).strip()
            for item in evidence.get("contradictions", [])
            if str(item).strip()
        ]
        disagreements.extend(unsupported_claims[:2])
        disagreements.extend(contradictions[:2])

        if not disagreements and skeptic_messages:
            skeptic_disagreement = self._extract_skeptic_disagreement(
                skeptic_messages[-1].get("content", "Evidence adequacy remains debated.")
            )
            if skeptic_disagreement:
                disagreements.append(skeptic_disagreement)

        supporting_evidence: list[str] = []
        if evidence.get("has_baseline"):
            supporting_evidence.append("explicit baseline comparison")
        if evidence.get("has_ablation"):
            supporting_evidence.append("ablation or component analysis")
        supporting_evidence.extend(datasets[:3])
        supporting_evidence.extend(metrics[:3])
        for message in support_messages:
            supporting_evidence.extend(
                str(item).strip()
                for item in message.get("evidence_refs", [])
                if str(item).strip()
            )
        supporting_evidence.extend(
            str(item.get("title", "")).strip()
            for item in supplementary_results[:2]
            if str(item.get("title", "")).strip()
        )

        return {
            "consensus": list(dict.fromkeys(item for item in consensus if item)),
            "disagreements": list(dict.fromkeys(item for item in disagreements if item)),
            "supporting_evidence": list(
                dict.fromkeys(item for item in supporting_evidence if item)
            ),
        }

    async def compute_confidence(
        self,
        debate_messages: list[dict],
        evidence: dict | None = None,
        supplementary_results: list[dict] | None = None,
    ) -> tuple[float, Literal["low", "medium", "high"]]:
        """Compute confidence score and conflict intensity from structured signals."""

        evidence = evidence or {}
        supplementary_results = supplementary_results or []
        support_messages = [msg for msg in debate_messages if msg.get("agent_role") == "support"]
        skeptic_messages = [msg for msg in debate_messages if msg.get("agent_role") == "skeptic"]

        datasets = [str(item).strip() for item in evidence.get("datasets", []) if str(item).strip()]
        metrics = [str(item).strip() for item in evidence.get("metrics", []) if str(item).strip()]
        unsupported_claims = [
            str(item).strip()
            for item in evidence.get("unsupported_claims", [])
            if str(item).strip()
        ]
        contradictions = [
            str(item).strip()
            for item in evidence.get("contradictions", [])
            if str(item).strip()
        ]

        positive_signals = float(len(support_messages))
        positive_signals += min(len(datasets), 3)
        positive_signals += min(len(metrics), 3)
        positive_signals += 2.0 if evidence.get("has_baseline") else 0.0
        positive_signals += 2.0 if evidence.get("has_ablation") else 0.0
        positive_signals += min(len(supplementary_results), 2)

        negative_signals = float(len(skeptic_messages))
        negative_signals += 2.0 if not evidence.get("has_baseline") else 0.0
        negative_signals += 2.0 if not evidence.get("has_ablation") else 0.0
        negative_signals += 1.0 if not metrics else 0.0
        negative_signals += min(len(unsupported_claims), 2) * 2.0
        negative_signals += min(len(contradictions), 2) * 2.0

        total = max(positive_signals + negative_signals, 1.0)
        evidence_coverage = sum(
            1
            for flag in (
                bool(datasets),
                bool(metrics),
                bool(evidence.get("has_baseline")),
                bool(evidence.get("has_ablation")),
            )
            if flag
        )
        coverage_bonus = (evidence_coverage / 4.0) * 25.0
        contradiction_penalty = float(len(contradictions) * 10 + len(unsupported_claims) * 5)

        confidence = ((positive_signals / total) * 70.0) + coverage_bonus - contradiction_penalty
        confidence = max(5.0, min(95.0, confidence))

        balance_ratio = abs(positive_signals - negative_signals) / total
        if positive_signals >= 5.0 and negative_signals >= 5.0 and balance_ratio <= 0.25:
            intensity: Literal["low", "medium", "high"] = "high"
        elif negative_signals >= 3.0 or balance_ratio <= 0.5:
            intensity = "medium"
        else:
            intensity = "low"

        return round(confidence, 2), intensity

    def _clean_sentence(self, text: str) -> str:
        normalized = " ".join(str(text).split()).strip()
        if not normalized:
            return ""
        return normalized.rstrip(".")

    def _first_sentence(self, text: str) -> str:
        normalized = " ".join(str(text).split()).strip()
        if not normalized:
            return "Evidence adequacy remains debated."
        sentence = normalized.split(".")[0].strip()
        if not sentence:
            return "Evidence adequacy remains debated."
        if sentence.endswith("."):
            return sentence
        return f"{sentence}."

    def _extract_skeptic_disagreement(self, text: str) -> str | None:
        normalized = " ".join(str(text).split()).strip()
        if not normalized:
            return None

        positive_markers = (
            "no major blocking gap",
            "no blocking gap remains",
            "no major blocker",
            "no major blocking issue",
            "no significant blocking issue",
            "support case is mostly credible",
            "support case is credible",
            "mostly credible",
            "overall credible",
            "broadly convincing",
        )
        negative_markers = (
            "unclear",
            "missing",
            "insufficient",
            "concern",
            "weakness",
            "risk",
            "gap",
            "unsupported",
            "contradiction",
            "limitation",
            "under-specified",
            "not demonstrated",
            "not shown",
            "fails",
            "failure",
            "questionable",
        )

        sentences = [
            self._clean_sentence(segment)
            for segment in normalized.replace("?", ".").replace("!", ".").split(".")
        ]
        for sentence in sentences:
            if not sentence:
                continue
            lowered = sentence.casefold()
            if any(marker in lowered for marker in positive_markers):
                continue
            if any(marker in lowered for marker in negative_markers):
                return f"{sentence}."
        return None
