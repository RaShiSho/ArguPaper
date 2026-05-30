"""Structured extraction from paper markdown."""

import re


class StructuredExtractor:
    """Extracts structured information from paper markdown."""

    COMMON_DATASETS = [
        "ImageNet",
        "COCO",
        "SQuAD",
        "MNIST",
        "CIFAR-10",
        "CIFAR10",
        "WMT",
        "GLUE",
        "SuperGLUE",
        "LibriSpeech",
    ]
    COMMON_METRICS = ["accuracy", "f1", "bleu", "rouge", "auc", "precision", "recall"]

    async def extract_abstract(self, markdown: str) -> dict:
        """Extract structured abstract."""

        abstract = self._extract_section(markdown, ["abstract"])
        intro = self._extract_section(markdown, ["introduction", "overview", "background"])
        method = self._extract_section(markdown, ["method", "approach", "model"])
        experiments = self._extract_section(markdown, ["experiment", "evaluation", "results"])
        conclusion = self._extract_section(markdown, ["conclusion", "discussion"])

        base_text = abstract or intro or markdown
        return {
            "problem": self._truncate(base_text, 260),
            "method": self._truncate(method or base_text, 260),
            "experiment": self._truncate(experiments or base_text, 260),
            "conclusion": self._truncate(conclusion or experiments or base_text, 260),
        }

    async def extract_experiments(self, markdown: str) -> dict:
        """Extract experiment information."""

        experiment_text = self._extract_section(markdown, ["experiment", "evaluation", "results"])
        haystack = experiment_text or markdown
        datasets = [name for name in self.COMMON_DATASETS if name.lower() in haystack.lower()]
        metrics = [name for name in self.COMMON_METRICS if re.search(rf"\b{name}\b", haystack, re.I)]
        sample_sizes = re.findall(r"\b\d{3,}\b", haystack)
        return {
            "datasets": datasets[:5],
            "metrics": metrics[:5],
            "sample_sizes": sample_sizes[:5],
            "has_baseline": bool(re.search(r"\bbaseline\b", haystack, re.I)),
            "has_ablation": bool(re.search(r"\bablation\b", haystack, re.I)),
        }

    async def extract_method(self, markdown: str) -> dict:
        """Extract method details."""

        method_text = self._extract_section(markdown, ["method", "approach", "model"])
        limitations_text = self._extract_section(markdown, ["limitation", "discussion"])
        assumptions = re.findall(r"assum\w+[^.]{0,80}\.", method_text or markdown, re.I)
        return {
            "details": self._truncate(method_text or markdown, 400),
            "assumptions": assumptions[:3],
            "limitations": self._truncate(limitations_text, 220) if limitations_text else "",
        }

    def _extract_section(self, markdown: str, keywords: list[str]) -> str:
        lines = markdown.splitlines()
        collected: list[str] = []
        capture = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip().lower()
                if any(keyword in heading for keyword in keywords):
                    capture = True
                    collected = []
                    continue
                if capture:
                    break
            elif capture:
                collected.append(stripped)
        return "\n".join(line for line in collected if line).strip()

    def _truncate(self, text: str, limit: int) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."
