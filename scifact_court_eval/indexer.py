"""Index SciFact sentence chunks into an isolated Milvus collection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from argupaper.config import Config
from argupaper.services.rag import MilvusChunk, MilvusConfig, MilvusVectorStore, OllamaEmbeddingClient

from scifact_court_eval.loaders import scifact_chunk_id
from scifact_court_eval.models import ScifactChunkRecord, ScifactDocument

SCIFACT_COLLECTION = "scifact_court_eval_chunks"
SCIFACT_PAPER_ID = "scifact"
SCIFACT_SOURCE = "scifact/corpus.jsonl"
ProgressCallback = Callable[[str], None] | None
EventCallback = Callable[[str, dict[str, Any]], None] | None


class ScifactIndexer:
    """Build and clean the isolated SciFact Milvus collection."""

    def __init__(
        self,
        config: Config,
        *,
        collection: str = SCIFACT_COLLECTION,
    ) -> None:
        self.config = config
        self.collection = collection
        self.embedding_client = OllamaEmbeddingClient(config.rag.embedding)
        self.vector_store = MilvusVectorStore(
            MilvusConfig(uri=config.rag.milvus.uri, collection=collection),
            default_dimension=config.rag.vector_dim,
        )

    async def close(self) -> None:
        """Close network and Milvus clients."""

        await self.embedding_client.close()
        self.vector_store.close()

    async def index_corpus(
        self,
        corpus: dict[int, ScifactDocument],
        *,
        split: str,
        batch_size: int = 32,
        rebuild: bool = False,
        progress_callback: ProgressCallback = None,
        event_callback: EventCallback = None,
    ) -> int:
        """Index all SciFact abstract sentences into the isolated collection."""

        records = list(self.iter_chunk_records(corpus, split=split))
        if rebuild:
            self.drop_collection()
        indexed = 0
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            if progress_callback is not None:
                progress_callback(
                    f"Indexing SciFact chunks {start + 1}-{start + len(batch)} of {len(records)} "
                    f"into {self.collection}..."
                )
            if event_callback is not None:
                event_callback(
                    "index_progress",
                    {
                        "collection": self.collection,
                        "batch_start": start + 1,
                        "batch_end": start + len(batch),
                        "total_chunks": len(records),
                        "batch_size": len(batch),
                    },
                )
            embeddings = await self._embed_batch(batch, progress_callback=progress_callback)
            chunks = [
                self._to_milvus_chunk(record, vector)
                for record, vector in zip(batch, embeddings, strict=True)
            ]
            indexed += self.vector_store.upsert(chunks)
        return indexed

    def cleanup(self) -> int | None:
        """Delete SciFact eval chunks without touching the default paper_chunks collection."""

        return self.vector_store.delete_by_paper(SCIFACT_PAPER_ID)

    def drop_collection(self) -> bool:
        """Drop only the isolated SciFact evaluation collection."""

        client = self.vector_store._get_client("drop SciFact eval collection")  # noqa: SLF001
        if not client.has_collection(collection_name=self.collection):
            return False
        try:
            client.drop_collection(collection_name=self.collection)
        except TypeError:
            client.drop_collection(self.collection)
        return True

    def collection_exists(self) -> bool:
        """Return whether the isolated evaluation collection exists."""

        client = self.vector_store._get_client("check SciFact eval collection")  # noqa: SLF001
        return bool(client.has_collection(collection_name=self.collection))

    def iter_chunk_records(
        self,
        corpus: dict[int, ScifactDocument],
        *,
        split: str,
    ) -> list[ScifactChunkRecord]:
        """Build sentence-level chunk records from the SciFact corpus."""

        records: list[ScifactChunkRecord] = []
        for doc_id in sorted(corpus):
            document = corpus[doc_id]
            for sentence_idx, sentence in enumerate(document.abstract):
                text = sentence.strip()
                if not text:
                    continue
                records.append(
                    ScifactChunkRecord(
                        chunk_id=scifact_chunk_id(document.doc_id, sentence_idx),
                        doc_id=document.doc_id,
                        sentence_idx=sentence_idx,
                        title=document.title,
                        text=text,
                        gold_split=split,
                    )
                )
        return records

    def _to_milvus_chunk(self, record: ScifactChunkRecord, vector: list[float]) -> MilvusChunk:
        return MilvusChunk(
            chunk_id=record.chunk_id,
            paper_id=SCIFACT_PAPER_ID,
            chunk_index=(record.doc_id * 1000) + record.sentence_idx,
            text=record.text,
            vector=vector,
            metadata={
                "doc_id": record.doc_id,
                "sentence_idx": record.sentence_idx,
                "title": record.title,
                "gold_split": record.gold_split,
                "source": SCIFACT_SOURCE,
                "section": "abstract",
                "section_type": "abstract",
            },
            section="abstract",
            source=SCIFACT_SOURCE,
        )

    async def _embed_batch(
        self,
        batch: list[ScifactChunkRecord],
        *,
        progress_callback: ProgressCallback = None,
    ) -> list[list[float]]:
        try:
            return await self.embedding_client.embed_texts([item.text for item in batch])
        except Exception as exc:  # noqa: BLE001 - retry smaller batches at service boundary
            if len(batch) <= 1:
                chunk_id = batch[0].chunk_id if batch else "unknown"
                raise RuntimeError(f"Embedding failed for SciFact chunk {chunk_id}: {exc}") from exc
            midpoint = len(batch) // 2
            if progress_callback is not None:
                progress_callback(
                    "Embedding batch failed; retrying with smaller batches "
                    f"({len(batch)} -> {midpoint}+{len(batch) - midpoint}). Error: {exc}"
                )
            left = await self._embed_batch(
                batch[:midpoint],
                progress_callback=progress_callback,
            )
            right = await self._embed_batch(
                batch[midpoint:],
                progress_callback=progress_callback,
            )
            return left + right
