"""Milvus dense vector store for local paper chunks."""

from __future__ import annotations

import json
import math
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
DELETE_PK_BATCH_SIZE = 100

VECTOR_FIELD = "vector"
PAPER_ID_FIELD = "paper_id"
VECTOR_METRIC_TYPE = "IP"
PAPER_ID_INDEX_TYPE = "INVERTED"
PAPER_ID_INDEX_NAME = "paper_id_idx"
OUTPUT_FIELDS = [
    "chunk_id",
    PAPER_ID_FIELD,
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
        self._use_insert_fallback: bool | None = None

    def ensure_collection(self, dimension: int | None = None) -> None:
        """Create the collection if needed and verify vector dimension."""

        expected_dimension = self._validate_dimension(
            self.default_dimension if dimension is None else dimension
        )
        client = self._get_client("ensure collection")
        try:
            if client.has_collection(collection_name=self.collection_name, timeout=self.timeout_seconds):
                self._validate_existing_dimension(client, expected_dimension)
                self._ensure_vector_index(client)
                self._ensure_paper_id_index(client)
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
        if self._should_use_insert_fallback(client):
            try:
                self._insert_records(client, records)
                return len(records)
            except (ConfigurationError, ExternalServiceError, InputValidationError):
                raise
            except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
                raise self._external_error("insert fallback for server version", exc) from exc
        try:
            client.upsert(
                collection_name=self.collection_name,
                data=records,
                timeout=self.timeout_seconds,
            )
            self._flush_collection(client)
            return len(records)
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            if self._is_unsupported_upsert(exc):
                try:
                    self._insert_records(client, records)
                    return len(records)
                except Exception as insert_exc:  # noqa: BLE001 - convert SDK-specific errors
                    raise self._external_error(
                        "insert fallback after unsupported upsert",
                        insert_exc,
                    ) from insert_exc
            raise self._external_error("upsert", exc) from exc

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        paper_id: str | None = None,
    ) -> list[MilvusSearchResult]:
        """Search dense vectors and return chunk payloads."""

        vector = self._normalize_vector(query_vector, field_name="query_vector")
        if top_k <= 0:
            raise InputValidationError("Milvus search top_k must be greater than 0.")

        client = self._get_client("search")
        try:
            if not client.has_collection(collection_name=self.collection_name, timeout=self.timeout_seconds):
                return []
            self._validate_existing_dimension(client, len(vector))
            self._load_collection(client)
            if paper_id is not None:
                self._ensure_paper_id_index(client)
            expression = self._paper_filter(paper_id) if paper_id is not None else ""
            results = client.search(
                collection_name=self.collection_name,
                data=[vector],
                anns_field=VECTOR_FIELD,
                filter=expression,
                limit=top_k,
                output_fields=OUTPUT_FIELDS,
                search_params={"metric_type": VECTOR_METRIC_TYPE, "params": {}},
                timeout=self.timeout_seconds,
            )
        except (ConfigurationError, ExternalServiceError, InputValidationError):
            raise
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            if paper_id is not None and self._is_filter_compatibility_error(exc):
                raise ExternalServiceError(self._filter_compatibility_message("search", exc)) from exc
            raise self._external_error("search", exc) from exc

        return self._parse_search_results(results)

    def delete_by_paper(self, paper_id: str) -> int | None:
        """Delete all chunks for one paper."""

        self._validate_paper_id(paper_id)
        client = self._get_client("delete by paper")
        try:
            if not client.has_collection(collection_name=self.collection_name, timeout=self.timeout_seconds):
                return 0
            return self._delete_by_paper_via_primary_keys(client, paper_id)
        except (ConfigurationError, ExternalServiceError, InputValidationError):
            raise
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("delete by paper", exc) from exc

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
            field_name=PAPER_ID_FIELD,
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

        client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=self._collection_index_params(client),
            timeout=self.timeout_seconds,
        )

    def _ensure_vector_index(self, client: Any) -> None:
        try:
            indexes = client.list_indexes(
                collection_name=self.collection_name,
                timeout=self.timeout_seconds,
            )
        except TypeError:
            indexes = client.list_indexes(collection_name=self.collection_name)

        if self._has_vector_index(indexes):
            return

        try:
            client.create_index(
                collection_name=self.collection_name,
                index_params=self._vector_index_params(client),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("ensure vector index", exc) from exc

    def _ensure_paper_id_index(self, client: Any) -> None:
        try:
            indexes = client.list_indexes(
                collection_name=self.collection_name,
                timeout=self.timeout_seconds,
            )
        except TypeError:
            indexes = client.list_indexes(collection_name=self.collection_name)

        if self._has_field_index(indexes, PAPER_ID_FIELD, PAPER_ID_INDEX_NAME):
            return

        try:
            client.create_index(
                collection_name=self.collection_name,
                index_params=self._paper_id_index_params(client),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise ExternalServiceError(self._filter_compatibility_message("ensure paper_id index", exc)) from exc

    def _collection_index_params(self, client: Any) -> Any:
        index_params = self._vector_index_params(client)
        self._add_paper_id_index(index_params)
        return index_params

    def _vector_index_params(self, client: Any) -> Any:
        index_params = client.prepare_index_params()
        index_params.add_index(field_name=VECTOR_FIELD, metric_type=VECTOR_METRIC_TYPE)
        return index_params

    def _paper_id_index_params(self, client: Any) -> Any:
        index_params = client.prepare_index_params()
        self._add_paper_id_index(index_params)
        return index_params

    def _add_paper_id_index(self, index_params: Any) -> None:
        index_params.add_index(
            field_name=PAPER_ID_FIELD,
            index_type=PAPER_ID_INDEX_TYPE,
            index_name=PAPER_ID_INDEX_NAME,
        )

    def _has_vector_index(self, indexes: Any) -> bool:
        if not indexes:
            return False
        if all(isinstance(index, str) for index in indexes):
            return True
        for index in indexes:
            if isinstance(index, str) and index == VECTOR_FIELD:
                return True
            if isinstance(index, dict) and index.get("field_name") == VECTOR_FIELD:
                return True
        return False

    def _has_field_index(self, indexes: Any, field_name: str, index_name: str) -> bool:
        if not indexes:
            return False
        for index in indexes:
            if isinstance(index, str) and index in {field_name, index_name}:
                return True
            if not isinstance(index, dict):
                continue
            if index.get("field_name") == field_name:
                return True
            if index.get("index_name") == index_name:
                return True
        return False

    def _flush_collection(self, client: Any) -> None:
        flush = getattr(client, "flush", None)
        if not callable(flush):
            return
        try:
            self._call_collection_method(flush)
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("flush collection", exc) from exc

    def _load_collection(self, client: Any) -> None:
        load_collection = getattr(client, "load_collection", None)
        if not callable(load_collection):
            return
        try:
            self._call_collection_method(load_collection)
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("load collection", exc) from exc

    def _call_collection_method(self, method: Any) -> None:
        try:
            method(collection_name=self.collection_name, timeout=self.timeout_seconds)
        except TypeError:
            method(collection_name=self.collection_name)

    def _insert_records(self, client: Any, records: list[dict[str, Any]]) -> None:
        client.insert(
            collection_name=self.collection_name,
            data=records,
            timeout=self.timeout_seconds,
        )
        self._flush_collection(client)

    def _should_use_insert_fallback(self, client: Any) -> bool:
        if self._use_insert_fallback is not None:
            return self._use_insert_fallback

        get_server_version = getattr(client, "get_server_version", None)
        if not callable(get_server_version):
            self._use_insert_fallback = False
            return self._use_insert_fallback

        try:
            version = str(get_server_version())
        except Exception:
            self._use_insert_fallback = False
            return self._use_insert_fallback

        match = re.search(r"v?(\d+)\.(\d+)", version)
        if match is None:
            self._use_insert_fallback = False
        else:
            major = int(match.group(1))
            minor = int(match.group(2))
            self._use_insert_fallback = (major, minor) < (2, 3)
        return self._use_insert_fallback

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
        vector = self._normalize_vector(chunk.vector, field_name=f"vector for chunk {chunk_id}")
        metadata_json = self._metadata_to_json(chunk.metadata)
        section = self._validate_optional_text(chunk.section, "section", SECTION_MAX_LENGTH)
        source = self._validate_optional_text(chunk.source, "source", SOURCE_MAX_LENGTH)
        return {
            "chunk_id": chunk_id,
            PAPER_ID_FIELD: paper_id,
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
        return f"{PAPER_ID_FIELD} == '{self._validate_paper_id(paper_id)}'"

    def _chunk_id_filter(self, chunk_ids: list[str]) -> str:
        if not chunk_ids:
            raise InputValidationError("Milvus chunk_id filter requires at least one chunk_id.")
        encoded_ids = ", ".join(json.dumps(chunk_id) for chunk_id in chunk_ids)
        return f"chunk_id in [{encoded_ids}]"

    def _delete_by_paper_via_primary_keys(self, client: Any, paper_id: str) -> int | None:
        chunk_ids = self._query_chunk_ids_by_paper(client, paper_id)
        if not chunk_ids:
            return 0

        total_deleted = 0
        saw_unknown_count = False
        for start in range(0, len(chunk_ids), DELETE_PK_BATCH_SIZE):
            batch = chunk_ids[start : start + DELETE_PK_BATCH_SIZE]
            try:
                result = client.delete(
                    collection_name=self.collection_name,
                    filter=self._chunk_id_filter(batch),
                    timeout=self.timeout_seconds,
                )
            except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
                raise self._external_error("delete by paper primary-key fallback", exc) from exc
            deleted_count = self._deleted_count(result)
            if deleted_count is None:
                saw_unknown_count = True
            else:
                total_deleted += deleted_count
        return None if saw_unknown_count else total_deleted

    def _query_chunk_ids_by_paper(self, client: Any, paper_id: str) -> list[str]:
        try:
            self._load_collection(client)
            rows = client.query(
                collection_name=self.collection_name,
                filter=self._paper_filter(paper_id),
                output_fields=["chunk_id"],
                limit=16384,
                timeout=self.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - convert SDK-specific errors at the boundary
            raise self._external_error("query chunk ids for delete fallback", exc) from exc

        chunk_ids: list[str] = []
        for row in rows or []:
            if isinstance(row, dict):
                chunk_id = str(row.get("chunk_id", "")).strip()
                if chunk_id:
                    chunk_ids.append(chunk_id)
        return chunk_ids

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
            numeric_value = float(value)
            if not math.isfinite(numeric_value):
                raise InputValidationError(
                    f"Milvus {field_name} contains a non-finite value at index {index}."
                )
            normalized.append(numeric_value)
        return normalized

    def _normalize_vector(self, vector: list[float], *, field_name: str) -> list[float]:
        values = self._validate_vector(vector, field_name=field_name)
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0.0:
            raise InputValidationError(f"Milvus {field_name} must not be an all-zero vector.")
        return [value / norm for value in values]

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

    def _is_unsupported_upsert(self, exc: Exception) -> bool:
        message = str(exc)
        return "Upsert" in message and (
            "UNIMPLEMENTED" in message or "unknown method Upsert" in message
        )

    def _is_filter_compatibility_error(self, exc: Exception) -> bool:
        message = str(exc)
        markers = [
            "Unsupported field type",
            "cannot parse expression",
            "failed to create query plan",
            "field paper_id",
            f"field {PAPER_ID_FIELD}",
        ]
        return any(marker in message for marker in markers)

    def _filter_compatibility_message(self, operation: str, exc: Exception) -> str:
        return (
            "Milvus RAG collection is not compatible with paper_id filtered search "
            f"(operation={operation}; uri={self.config.uri}; collection={self.collection_name}; "
            f"index_field={PAPER_ID_FIELD}; index_type={PAPER_ID_INDEX_TYPE}; "
            f"error={type(exc).__name__}: {exc}). "
            "Rebuild the RAG collection and reindex papers manually before using scoped RAG search."
        )

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
