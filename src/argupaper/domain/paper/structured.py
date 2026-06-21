"""Structured extraction from paper markdown."""

import re


class StructuredExtractor:
    """Extracts structured information from paper markdown."""

    EXPERIMENT_SECTION_KEYWORDS = [
        "experiment",
        "evaluation",
        "results",
        "benchmark",
        "dataset",
        "metrics",
        "empirical",
        "ablation",
        "implementation details",
        "experimental setup",
        "performance",
    ]
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
        "GSM8K",
        "HumanEval",
        "MMLU",
        "PubMedQA",
        "HellaSwag",
        "ARC",
        "DROP",
        "TruthfulQA",
        "BBH",
        "MATH",
        "MultiArith",
        "HotpotQA",
        "Natural Questions",
        "TriviaQA",
        "FEVER",
        "WinoGrande",
        "SST-2",
        "CoNLL",
        "WikiText-103",
        "LAMBADA",
        "MS MARCO",
        "TREC",
        "MovieLens",
        "Yelp",
        "Amazon Reviews",
        "Cora",
        "Citeseer",
        "PubMed",
        "OGBN-Arxiv",
        "QM9",
        "MoleculeNet",
    ]
    COMMON_METRICS = [
        "accuracy",
        "f1",
        "f1-score",
        "exact match",
        "em",
        "bleu",
        "rouge",
        "rouge-l",
        "meteor",
        "auc",
        "auroc",
        "auprc",
        "precision",
        "recall",
        "map",
        "mrr",
        "ndcg",
        "mae",
        "rmse",
        "mse",
        "perplexity",
        "wer",
        "cer",
        "pass@1",
        "pass@k",
        "hit@1",
        "hit@10",
    ]
    DATASET_STOPWORDS = {
        "Ablation",
        "Appendix",
        "Baseline",
        "Figure",
        "Metric",
        "Metrics",
        "Method",
        "Model",
        "Results",
        "Table",
        "The",
        "This",
        "Training",
        "Validation",
        "We",
    }

    async def extract_abstract(self, markdown: str) -> dict:
        """Extract structured abstract."""

        abstract = self._extract_section(markdown, ["abstract"])
        intro = self._extract_section(markdown, ["introduction", "overview", "background"])
        method = self._extract_section(markdown, ["method", "approach", "model"])
        experiments = self._extract_section(markdown, self.EXPERIMENT_SECTION_KEYWORDS)
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

        experiment_text = self._extract_section(markdown, self.EXPERIMENT_SECTION_KEYWORDS)
        haystack = experiment_text or markdown
        datasets = self._extract_datasets(haystack)
        metrics = self._extract_metrics(haystack)
        sample_sizes = re.findall(r"\b\d{3,}\b", haystack)
        return {
            "datasets": datasets[:5],
            "metrics": metrics[:5],
            "sample_sizes": sample_sizes[:5],
            "has_baseline": bool(re.search(r"\bbaseline\b", haystack, re.I)),
            "has_ablation": bool(re.search(r"\bablation\b", haystack, re.I)),
            "support_snippets": self._extract_support_snippets(haystack, datasets, metrics),
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
        sections = self._extract_sections(markdown, keywords)
        return "\n\n".join(sections).strip()

    def _extract_sections(self, markdown: str, keywords: list[str]) -> list[str]:
        lines = markdown.splitlines()
        sections: list[str] = []
        collected: list[str] = []
        capture = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip().lower()
                if capture and collected:
                    sections.append("\n".join(line for line in collected if line).strip())
                    collected = []
                if any(keyword in heading for keyword in keywords):
                    capture = True
                    continue
                if capture:
                    capture = False
            elif capture:
                collected.append(stripped)
        if capture and collected:
            sections.append("\n".join(line for line in collected if line).strip())
        return [section for section in sections if section]

    def _extract_datasets(self, text: str) -> list[str]:
        candidates: list[str] = []
        for name in self.COMMON_DATASETS:
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", text, re.I):
                candidates.append(name)

        phrase_patterns = [
            r"\b(?:on|using|from|over|with)\s+(?:the\s+)?([A-Z][A-Za-z0-9_.+-]*(?:[-/][A-Za-z0-9_.+-]+)?(?:\s+[A-Z][A-Za-z0-9_.+-]*){0,2})",
            r"\b(?:datasets?|benchmarks?)\s+(?:include|includes|are|were|contain|contains)\s+([^.;:\n]+)",
            r"\b(?:evaluated|trained|tested|fine-tuned)\s+(?:on|using)\s+([^.;:\n]+)",
        ]
        for pattern in phrase_patterns:
            for match in re.findall(pattern, text):
                candidates.extend(self._split_candidate_names(match))

        benchmark_tokens = re.findall(
            r"\b[A-Z][A-Za-z0-9]*(?:QA|Eval|GLUE|Bench|Set|Net|Corpus|Bank|Text|Code|Math|MATH)\b(?:-\d+)?",
            text,
        )
        candidates.extend(benchmark_tokens)

        acronym_datasets = re.findall(r"\b[A-Z]{2,}(?:-\d+|[A-Za-z]{2,})\b", text)
        candidates.extend(acronym_datasets)
        metric_names = {
            self._canonical_metric(metric).casefold()
            for metric in [*self.COMMON_METRICS, *self._extract_metrics(text)]
        }
        return self._unique_names(candidates, max_items=8, excluded=metric_names)

    def _extract_metrics(self, text: str) -> list[str]:
        candidates: list[str] = []
        for metric in self.COMMON_METRICS:
            escaped = re.escape(metric)
            if re.search(rf"(?<![A-Za-z0-9@-]){escaped}(?![A-Za-z0-9@-])", text, re.I):
                candidates.append(self._canonical_metric(metric))

        metric_patterns = [
            r"\b(?:F1|EM|mAP|MRR|NDCG@?\d*|AUROC|AUPRC|MAE|RMSE|MSE|BLEU|ROUGE(?:-[L12])?|METEOR|WER|CER)\b",
            r"\b(?:Pass|pass)@\d+\b",
            r"\b(?:Hit|hit)@\d+\b",
            r"\b(?:exact match|accuracy|precision|recall|perplexity)\b",
        ]
        for pattern in metric_patterns:
            candidates.extend(re.findall(pattern, text, re.I))
        return self._unique_names([self._canonical_metric(item) for item in candidates], max_items=8)

    def _split_candidate_names(self, text: str) -> list[str]:
        normalized = re.sub(r"\band\b", ",", text, flags=re.I)
        parts = re.split(r",|/|;|\(|\)", normalized)
        return [part.strip(" .:-") for part in parts if part.strip(" .:-")]

    def _unique_names(
        self,
        candidates: list[str],
        max_items: int,
        excluded: set[str] | None = None,
    ) -> list[str]:
        excluded = excluded or set()
        normalized: dict[str, str] = {}
        for candidate in candidates:
            cleaned = re.sub(r"\s+", " ", candidate).strip(" .,:;")
            if not self._is_valid_dataset_or_metric(cleaned):
                continue
            key = cleaned.casefold()
            if key in excluded:
                continue
            normalized.setdefault(key, cleaned)
            if len(normalized) >= max_items:
                break
        return list(normalized.values())

    def _is_valid_dataset_or_metric(self, value: str) -> bool:
        if not value or len(value) < 2:
            return False
        if value in self.DATASET_STOPWORDS:
            return False
        if value.casefold() in {"and", "or", "the", "our", "their", "dataset", "datasets"}:
            return False
        if len(value.split()) > 4:
            return False
        return True

    def _canonical_metric(self, metric: str) -> str:
        normalized = metric.strip()
        aliases = {
            "em": "EM",
            "f1": "F1",
            "map": "mAP",
            "mrr": "MRR",
            "ndcg": "NDCG",
            "auc": "AUC",
            "auroc": "AUROC",
            "auprc": "AUPRC",
            "mae": "MAE",
            "rmse": "RMSE",
            "mse": "MSE",
            "bleu": "BLEU",
            "rouge": "ROUGE",
            "rouge-l": "ROUGE-L",
            "meteor": "METEOR",
            "wer": "WER",
            "cer": "CER",
        }
        return aliases.get(normalized.casefold(), normalized)

    def _extract_support_snippets(
        self,
        text: str,
        datasets: list[str],
        metrics: list[str],
    ) -> list[str]:
        markers = [*datasets, *metrics]
        if not markers:
            return []
        raw_units = [
            unit.strip()
            for unit in re.split(r"(?<=[.!?])\s+|\n", text)
            if unit.strip()
        ]
        snippets: list[str] = []
        for unit in raw_units:
            lowered = unit.casefold()
            if any(marker.casefold() in lowered for marker in markers):
                snippets.append(self._truncate(unit, 220))
            if len(snippets) >= 6:
                break
        return snippets

    def _truncate(self, text: str, limit: int) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rstrip() + "..."
