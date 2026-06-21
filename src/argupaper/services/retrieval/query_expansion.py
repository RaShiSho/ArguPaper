"""Query expansion for semantic search."""


class QueryExpander:
    """Expands queries with semantic synonyms and related terms."""

    SYNONYMS = {
        "rag": ["retrieval augmented generation"],
        "llm": ["large language model"],
        "nlp": ["natural language processing"],
        "qa": ["question answering"],
        "transformer": ["attention model"],
    }
    RELATED_METHODS = {
        "retrieval": ["dense retrieval", "sparse retrieval"],
        "generation": ["sequence generation", "instruction tuning"],
        "reasoning": ["chain of thought", "self consistency"],
        "attention": ["self attention", "cross attention"],
    }
    RELATED_DATASETS = {
        "question": ["SQuAD", "Natural Questions"],
        "translation": ["WMT", "IWSLT"],
        "vision": ["ImageNet", "COCO"],
        "summarization": ["CNN/DailyMail", "XSum"],
    }

    def expand(self, query: str) -> dict:
        """Expand query with synonyms, methods, and datasets."""

        normalized_tokens = [token.strip().lower() for token in query.split() if token.strip()]
        synonyms: list[str] = []
        related_methods: list[str] = []
        related_datasets: list[str] = []

        for token in normalized_tokens:
            synonyms.extend(self.SYNONYMS.get(token, []))
            for key, values in self.RELATED_METHODS.items():
                if key in token:
                    related_methods.extend(values)
            for key, values in self.RELATED_DATASETS.items():
                if key in token:
                    related_datasets.extend(values)

        expanded_queries = [query]
        expanded_queries.extend(f"{query} {value}" for value in synonyms[:2])
        expanded_queries.extend(f"{query} {value}" for value in related_methods[:1])
        expanded_queries.extend(f"{query} {value}" for value in related_datasets[:1])

        return {
            "expanded_queries": list(
                dict.fromkeys(item.strip() for item in expanded_queries if item.strip())
            ),
            "synonyms": list(dict.fromkeys(synonyms)),
            "related_methods": list(dict.fromkeys(related_methods)),
            "related_datasets": list(dict.fromkeys(related_datasets)),
        }
