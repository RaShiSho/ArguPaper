"""Milvus dense vector store for local paper chunks."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argupaper.services.rag.config import MilvusConfig
from argupaper.workflows.errors import ConfigurationError, ExternalServiceError, InputValidationError

COLLECTION_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PAPER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")

CHUNK_ID_MAX_LENGTH = 256
PAPER_ID_MAX_LENGTH = 256
TEXT_MAX_LENGTH = 65535
METADATA_MAX_LENGTH = 65535
SECTION_MAX_LENGTH = 1024
SOURCE_MAX_LENGTH = 2048

VECTOR_FIELD = "vector"
OUTPUT_FIELDS = [
    "chunk_id",
    "paper_id",
    "chunk_index",
    "section",
    "source",
    "metadata_json",
    "text",
]


@dataclass(frozen=True)
class MilvusChunk:
    """One paper chunk ready for vector storage."""

    chunk_id: str
    paper_id: str
    chunk_index: int
    text: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    section: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class MilvusSearchResult:
    """One chunk returned by vector search."""

    chunk_id: str
    paper_id: str
    chunk_index: int
    text: str
    metadata: dict[str, Any]
    score: float
    section: str | None = None
    source: str | None = None


class MilvusVectorStore:
    """Small dense-vector wrapper around MilvusClient."""

    def __init__(
        self,
        config: MilvusConfig,
        *,
        timeout_seconds: int = 30,
        default_dimension: int = 1024,
    ) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.default_dimension = default_dimension
        self.collection_name = self._validate_collection_name(config.collection)
        self._client: Any | None = None
        self._data_type: Any | None = None

    def ensure_collection(self, dimension: int | None = None) -> None:
        """Create the collection if needed and verify vector dimension."""

        expected_dimension = self._validate_dimension(
            self.default_dimension if dimension is None else dimension
        )
        client = self._get_client("ensure collection")
        try:
            if client.has_collection(collection_name=self.collection_name, timeout=self.timeout_seconds):
                self._validate_existing_dimension(client, expected_dimension)
                return
            self._create_collection(client, expected_dimension)
        except (ConfigurationError, ExternalServiceError, InputValidationError):
            raise
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("ensure collection", exc) from exc

    def upsert(self, chunks: list[MilvusChunk]) -> int:
        """Upsert paper chunks and return the number of submitted rows."""

        if not chunks:
            raise InputValidationError("Milvus upsert requires at least one chunk.")

        records = [self._chunk_to_record(chunk) for chunk in chunks]
        dimension = len(records[0][VECTOR_FIELD])
        for record in records:
            if len(record[VECTOR_FIELD]) != dimension:
                raise InputValidationError("All Milvus chunk vectors must have the same dimension.")

        self.ensure_collection(dimension)
        client = self._get_client("upsert")
        try:
            client.upsert(
                collection_name=self.collection_name,
                data=records,
                timeout=self.timeout_seconds,
            )
            return len(records)
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("upsert", exc) from exc

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        paper_id: str | None = None,
    ) -> list[MilvusSearchResult]:
        """Search dense vectors and return chunk payloads."""

        vector = self._validate_vector(query_vector, field_name="query_vector")
        if top_k <= 0:
            raise InputValidationError("Milvus search top_k must be greater than 0.")

        client = self._get_client("search")
        try:
            if not client.has_collection(collection_name=self.collection_name, timeout=self.timeout_seconds):
                return []
            self._validate_existing_dimension(client, len(vector))
            expression = self._paper_filter(paper_id) if paper_id is not None else ""
            results = client.search(
                collection_name=self.collection_name,
                data=[vector],
                anns_field=VECTOR_FIELD,
                filter=expression,
                limit=top_k,
                output_fields=OUTPUT_FIELDS,
                search_params={"metric_type": "COSINE", "params": {}},
                timeout=self.timeout_seconds,
            )
        except (ConfigurationError, ExternalServiceError, InputValidationError):
            raise
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("search", exc) from exc

        return self._parse_search_results(results)

    def delete_by_paper(self, paper_id: str) -> int | None:
        """Delete all chunks for one paper."""

        expression = self._paper_filter(paper_id)
        client = self._get_client("delete by paper")
        try:
            if not client.has_collection(collection_name=self.collection_name, timeout=self.timeout_seconds):
                return 0
            result = client.delete(
                collection_name=self.collection_name,
                filter=expression,
                timeout=self.timeout_seconds,
            )
        except (ConfigurationError, ExternalServiceError, InputValidationError):
            raise
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("delete by paper", exc) from exc
        return self._deleted_count(result)

    def close(self) -> None:
        """Close the underlying Milvus client when supported."""

        client = self._client
        self._client = None
        if client is None:
            return
        close = getattr(client, "close", None)
        if callable(close):
            close()

    def _get_client(self, operation: str) -> Any:
        if self._client is not None:
            return self._client

        DataType, MilvusClient = self._import_milvus()

        self._data_type = DataType
        uri = self.config.uri.strip()
        self._ensure_local_uri_parent(uri)
        try:
            self._client = MilvusClient(uri=uri)
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error(operation, exc) from exc
        return self._client

    def _import_milvus(self) -> tuple[Any, Any]:
        original_milvus_uri = os.environ.get("MILVUS_URI")
        os.environ["MILVUS_URI"] = "http://localhost:19530"
        try:
            try:
                from pymilvus import DataType, MilvusClient
            except ImportError as exc:
                raise ConfigurationError(
                    "pymilvus is not installed. Run `uv sync` before using MilvusVectorStore."
                ) from exc
            except Exception as exc:  # noqa: BLE001 - convert SDK import/config errors
                raise ExternalServiceError(
                    "Milvus SDK failed to initialize while importing pymilvus: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            return DataType, MilvusClient
        finally:
            if original_milvus_uri is not None:
                os.environ["MILVUS_URI"] = original_milvus_uri
            else:
                os.environ.pop("MILVUS_URI", None)

    def _create_collection(self, client: Any, dimension: int) -> None:
        schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field(
            field_name="chunk_id",
            datatype=self._data_type.VARCHAR,
            is_primary=True,
            max_length=CHUNK_ID_MAX_LENGTH,
        )
        schema.add_field(
            field_name="paper_id",
            datatype=self._data_type.VARCHAR,
            max_length=PAPER_ID_MAX_LENGTH,
        )
        schema.add_field(field_name="chunk_index", datatype=self._data_type.INT64)
        schema.add_field(
            field_name="section",
            datatype=self._data_type.VARCHAR,
            max_length=SECTION_MAX_LENGTH,
        )
        schema.add_field(
            field_name="source",
            datatype=self._data_type.VARCHAR,
            max_length=SOURCE_MAX_LENGTH,
        )
        schema.add_field(
            field_name="metadata_json",
            datatype=self._data_type.VARCHAR,
            max_length=METADATA_MAX_LENGTH,
        )
        schema.add_field(
            field_name="text",
            datatype=self._data_type.VARCHAR,
            max_length=TEXT_MAX_LENGTH,
        )
        schema.add_field(field_name=VECTOR_FIELD, datatype=self._data_type.FLOAT_VECTOR, dim=dimension)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name=VECTOR_FIELD, metric_type="COSINE")
        client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
            timeout=self.timeout_seconds,
        )

    def _validate_existing_dimension(self, client: Any, expected_dimension: int) -> None:
        description = client.describe_collection(
            collection_name=self.collection_name,
            timeout=self.timeout_seconds,
        )
        actual_dimension = self._extract_vector_dimension(description)
        if actual_dimension is None:
            raise ExternalServiceError(
                "Milvus collection schema does not expose vector dimension "
                f"for '{self.collection_name}'."
            )
        if actual_dimension != expected_dimension:
            raise InputValidationError(
                "Milvus vector dimension mismatch: "
                f"collection '{self.collection_name}' has {actual_dimension}, "
                f"input has {expected_dimension}."
            )

    def _extract_vector_dimension(self, description: Any) -> int | None:
        fields = []
        if isinstance(description, dict):
            fields = description.get("fields") or description.get("schema", {}).get("fields") or []
        for field in fields:
            if not isinstance(field, dict) or field.get("name") != VECTOR_FIELD:
                continue
            params = field.get("params") or {}
            dimension = field.get("dim") or params.get("dim")
            if dimension is not None:
                return int(dimension)
        return None

    def _chunk_to_record(self, chunk: MilvusChunk) -> dict[str, Any]:
        chunk_id = self._validate_nonempty_text(chunk.chunk_id, "chunk_id", CHUNK_ID_MAX_LENGTH)
        paper_id = self._validate_paper_id(chunk.paper_id)
        text = self._validate_nonempty_text(chunk.text, "text", TEXT_MAX_LENGTH)
        if chunk.chunk_index < 0:
            raise InputValidationError("Milvus chunk_index must be greater than or equal to 0.")
        vector = self._validate_vector(chunk.vector, field_name=f"vector for chunk {chunk_id}")
        metadata_json = self._metadata_to_json(chunk.metadata)
        section = self._validate_optional_text(chunk.section, "section", SECTION_MAX_LENGTH)
        source = self._validate_optional_text(chunk.source, "source", SOURCE_MAX_LENGTH)
        return {
            "chunk_id": chunk_id,
            "paper_id": paper_id,
            "chunk_index": int(chunk.chunk_index),
            "section": section,
            "source": source,
            "metadata_json": metadata_json,
            "text": text,
            VECTOR_FIELD: vector,
        }

    def _parse_search_results(self, results: Any) -> list[MilvusSearchResult]:
        first_batch = results[0] if results else []
        parsed: list[MilvusSearchResult] = []
        for item in first_batch:
            entity = self._result_entity(item)
            parsed.append(
                MilvusSearchResult(
                    chunk_id=str(entity.get("chunk_id", "")),
                    paper_id=str(entity.get("paper_id", "")),
                    chunk_index=int(entity.get("chunk_index", 0)),
                    text=str(entity.get("text", "")),
                    metadata=self._json_to_metadata(str(entity.get("metadata_json", "{}"))),
                    score=float(self._result_score(item)),
                    section=self._none_if_empty(entity.get("section")),
                    source=self._none_if_empty(entity.get("source")),
                )
            )
        return parsed

    def _result_entity(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            entity = item.get("entity", item)
            return dict(entity) if isinstance(entity, dict) else {}
        entity = getattr(item, "entity", None)
        if isinstance(entity, dict):
            return dict(entity)
        return {}

    def _result_score(self, item: Any) -> float:
        if isinstance(item, dict):
            value = item.get("distance", item.get("score", 0.0))
        else:
            value = getattr(item, "distance", getattr(item, "score", 0.0))
        return float(value)

    def _metadata_to_json(self, metadata: dict[str, Any]) -> str:
        try:
            payload = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"Milvus chunk metadata must be JSON serializable: {exc}") from exc
        if len(payload) > METADATA_MAX_LENGTH:
            raise InputValidationError("Milvus chunk metadata_json is too long.")
        return payload

    def _json_to_metadata(self, payload: str) -> dict[str, Any]:
        try:
            data = json.loads(payload or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _paper_filter(self, paper_id: str) -> str:
        return f"paper_id == '{self._validate_paper_id(paper_id)}'"

    def _validate_paper_id(self, paper_id: str) -> str:
        value = self._validate_nonempty_text(paper_id, "paper_id", PAPER_ID_MAX_LENGTH)
        if not PAPER_ID_PATTERN.fullmatch(value):
            raise InputValidationError(
                "Milvus paper_id may only contain letters, digits, underscore, dot, colon, or hyphen."
            )
        return value

    def _validate_collection_name(self, collection_name: str) -> str:
        value = str(collection_name or "").strip()
        if not COLLECTION_NAME_PATTERN.fullmatch(value):
            raise InputValidationError(
                "Milvus collection name must start with a letter or underscore and contain only "
                "letters, digits, and underscores."
            )
        return value

    def _validate_dimension(self, dimension: int) -> int:
        if dimension <= 0:
            raise InputValidationError("Milvus vector dimension must be greater than 0.")
        return int(dimension)

    def _validate_vector(self, vector: list[float], *, field_name: str) -> list[float]:
        if not vector:
            raise InputValidationError(f"Milvus {field_name} must not be empty.")
        normalized: list[float] = []
        for index, value in enumerate(vector):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InputValidationError(
                    f"Milvus {field_name} contains a non-numeric value at index {index}."
                )
            normalized.append(float(value))
        return normalized

    def _validate_nonempty_text(self, value: str, field_name: str, max_length: int) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise InputValidationError(f"Milvus {field_name} must not be empty.")
        if len(normalized) > max_length:
            raise InputValidationError(f"Milvus {field_name} is too long.")
        return normalized

    def _validate_optional_text(self, value: str | None, field_name: str, max_length: int) -> str:
        if value is None:
            return ""
        normalized = str(value).strip()
        if len(normalized) > max_length:
            raise InputValidationError(f"Milvus {field_name} is too long.")
        return normalized

    def _deleted_count(self, result: Any) -> int | None:
        if isinstance(result, dict):
            for key in ("delete_count", "delete_cnt", "count"):
                if key in result:
                    return int(result[key])
        return None

    def _ensure_local_uri_parent(self, uri: str) -> None:
        if uri.endswith(".db") and "://" not in uri:
            Path(uri).expanduser().parent.mkdir(parents=True, exist_ok=True)

    def _external_error(self, operation: str, exc: Exception) -> ExternalServiceError:
        return ExternalServiceError(
            "Milvus operation failed "
            f"({operation}; uri={self.config.uri}; collection={self.collection_name}; "
            f"error={type(exc).__name__}: {exc})"
        )

    def _none_if_empty(self, value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None


__all__ = ["MilvusChunk", "MilvusSearchResult", "MilvusVectorStore"]
