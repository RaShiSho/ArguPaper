"""Claim to experiment alignment checker."""

import re
from typing import Any


class ClaimChecker:
    """Checks alignment between claims and experimental evidence."""

    CLAIM_KEYS = ("claim", "text", "content", "statement", "description", "title")
    EVIDENCE_KEYS = (
        "dataset",
        "metric",
        "support",
        "result",
        "finding",
        "evidence",
        "description",
        "text",
    )
    STOPWORDS = {
        "about",
        "after",
        "against",
        "also",
        "among",
        "and",
        "are",
        "because",
        "been",
        "being",
        "between",
        "both",
        "can",
        "could",
        "does",
        "for",
        "from",
        "has",
        "have",
        "into",
        "its",
        "more",
        "most",
        "our",
        "paper",
        "propose",
        "proposed",
        "show",
        "shows",
        "study",
        "that",
        "the",
        "their",
        "this",
        "through",
        "using",
        "was",
        "were",
        "with",
        "within",
    }
    STRONG_CLAIM_MARKERS = (
        "achieve",
        "better than",
        "effective",
        "improve",
        "improvement",
        "novel",
        "outperform",
        "reduce",
        "robust",
        "significant",
        "state-of-the-art",
        "superior",
    )
    COMPARISON_MARKERS = (
        "against",
        "baseline",
        "beat",
        "better",
        "compare",
        "comparison",
        "outperform",
        "state-of-the-art",
    )
    ABLATION_MARKERS = (
        "ablation",
        "component",
        "remove",
        "sensitivity",
        "variant",
        "without",
    )
    NEGATIVE_EVIDENCE_MARKERS = (
        "fails",
        "lower than",
        "no improvement",
        "not improve",
        "not outperform",
        "underperform",
        "worse",
    )
    POSITIVE_EVIDENCE_MARKERS = (
        "achieve",
        "higher than",
        "improve",
        "outperform",
        "state-of-the-art",
        "superior",
    )
    EMPTY_MARKERS = {"", "n/a", "na", "none", "not specified", "unknown"}

    def __init__(self, min_token_overlap: float = 0.14) -> None:
        self.min_token_overlap = min_token_overlap

    async def check_alignment(self, claims: list[dict], evidence: list[dict]) -> dict:
        """Check if claims are supported by evidence.

        Returns:
            dict with keys: aligned_claims, unsupported_claims, contradictions
        """

        claim_texts = [text for item in claims if (text := self._extract_claim_text(item))]
        evidence_texts = [text for item in evidence if (text := self._extract_evidence_text(item))]

        aligned_claims: list[dict[str, Any]] = []
        unsupported_claims: list[str] = []
        contradictions: list[str] = []

        for claim in claim_texts:
            match = self._best_evidence_match(claim, evidence_texts)
            contradiction = self._find_contradiction(claim, evidence_texts)
            if contradiction:
                contradictions.append(contradiction)

            if match is not None and contradiction is None:
                aligned_claims.append(
                    {
                        "claim": claim,
                        "evidence": self._truncate(match["evidence"], 180),
                        "score": round(float(match["score"]), 2),
                    }
                )
                continue

            if self._requires_direct_evidence(claim) or not evidence_texts:
                unsupported_claims.append(claim)

        return {
            "aligned_claims": aligned_claims,
            "unsupported_claims": list(dict.fromkeys(unsupported_claims)),
            "contradictions": list(dict.fromkeys(contradictions)),
        }

    async def check_sufficiency(self, evidence: list[dict]) -> dict:
        """Check if experimental evidence is sufficient.

        Returns:
            dict with keys: has_baseline, has_ablation, missing_analyses
        """

        evidence_text = " ".join(self._extract_evidence_text(item) for item in evidence)
        lowered = evidence_text.casefold()

        has_baseline = any(marker in lowered for marker in self.COMPARISON_MARKERS)
        has_ablation = any(marker in lowered for marker in self.ABLATION_MARKERS)
        has_dataset = any(self._has_value(item.get("dataset")) for item in evidence)
        has_metric = any(self._has_value(item.get("metric")) for item in evidence)

        missing_analyses: list[str] = []
        if not has_dataset:
            missing_analyses.append("dataset")
        if not has_metric:
            missing_analyses.append("metric")
        if not has_baseline:
            missing_analyses.append("baseline")
        if not has_ablation:
            missing_analyses.append("ablation")

        return {
            "has_baseline": has_baseline,
            "has_ablation": has_ablation,
            "has_dataset": has_dataset,
            "has_metric": has_metric,
            "missing_analyses": missing_analyses,
        }

    def _extract_claim_text(self, item: object) -> str:
        return self._extract_text(item, self.CLAIM_KEYS)

    def _extract_evidence_text(self, item: object) -> str:
        if isinstance(item, dict):
            values = [
                self._normalize_text(item[key])
                for key in self.EVIDENCE_KEYS
                if key in item and self._has_value(item[key])
            ]
            if values:
                return self._normalize_text(" ".join(values))
        return self._extract_text(item, self.EVIDENCE_KEYS)

    def _extract_text(self, item: object, preferred_keys: tuple[str, ...]) -> str:
        if isinstance(item, str):
            return self._normalize_text(item)
        if isinstance(item, dict):
            for key in preferred_keys:
                if key in item and self._has_value(item[key]):
                    return self._normalize_text(item[key])
            return self._normalize_text(" ".join(self._iter_text_values(item)))
        return self._normalize_text(item)

    def _iter_text_values(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            parts: list[str] = []
            for nested in value.values():
                parts.extend(self._iter_text_values(nested))
            return parts
        if isinstance(value, (list, tuple, set)):
            parts = []
            for nested in value:
                parts.extend(self._iter_text_values(nested))
            return parts
        return [str(value)]

    def _normalize_text(self, value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _has_value(self, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, (list, tuple, set)):
            return any(self._has_value(item) for item in value)
        normalized = self._normalize_text(value).casefold()
        return normalized not in self.EMPTY_MARKERS

    def _best_evidence_match(self, claim: str, evidence_texts: list[str]) -> dict[str, object] | None:
        claim_tokens = self._tokens(claim)
        if not claim_tokens:
            return None

        best_score = 0.0
        best_evidence = ""
        for evidence in evidence_texts:
            evidence_tokens = self._tokens(evidence)
            if not evidence_tokens:
                continue
            overlap = len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)
            marker_bonus = 0.08 if self._shares_marker(claim, evidence) else 0.0
            score = overlap + marker_bonus
            if score > best_score:
                best_score = score
                best_evidence = evidence

        if best_score < self.min_token_overlap:
            return None
        return {"evidence": best_evidence, "score": best_score}

    def _tokens(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.casefold())
            if token not in self.STOPWORDS
        }

    def _shares_marker(self, claim: str, evidence: str) -> bool:
        claim_lowered = claim.casefold()
        evidence_lowered = evidence.casefold()
        return any(
            marker in claim_lowered and marker in evidence_lowered
            for marker in (*self.STRONG_CLAIM_MARKERS, *self.COMPARISON_MARKERS)
        )

    def _requires_direct_evidence(self, claim: str) -> bool:
        lowered = claim.casefold()
        return any(marker in lowered for marker in self.STRONG_CLAIM_MARKERS)

    def _find_contradiction(self, claim: str, evidence_texts: list[str]) -> str | None:
        claim_lowered = claim.casefold()
        claim_is_positive = any(marker in claim_lowered for marker in self.POSITIVE_EVIDENCE_MARKERS)
        claim_is_negative = any(marker in claim_lowered for marker in self.NEGATIVE_EVIDENCE_MARKERS)

        for evidence in evidence_texts:
            evidence_lowered = evidence.casefold()
            evidence_is_positive = any(
                marker in evidence_lowered for marker in self.POSITIVE_EVIDENCE_MARKERS
            )
            evidence_is_negative = any(
                marker in evidence_lowered for marker in self.NEGATIVE_EVIDENCE_MARKERS
            )
            if claim_is_positive and evidence_is_negative:
                return (
                    f"Claim '{self._truncate(claim, 120)}' conflicts with evidence "
                    f"'{self._truncate(evidence, 120)}'."
                )
            if claim_is_negative and evidence_is_positive:
                return (
                    f"Claim '{self._truncate(claim, 120)}' conflicts with evidence "
                    f"'{self._truncate(evidence, 120)}'."
                )
        return None

    def _truncate(self, text: str, limit: int) -> str:
        normalized = self._normalize_text(text)
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."
