"""In-memory background job registry for local web analysis."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from argupaper.web.schemas import AnalyzeJobStatusResponse, JobProgressMessage, JobStatus
from argupaper.workflows.models import AnalyzeOptions, AnalyzeWorkflowResult


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(tz=timezone.utc)


@dataclass
class AnalyzeJobRecord:
    """Mutable in-memory state for one analyze job."""

    job_id: str
    upload_path: Path
    upload_filename: str
    options: AnalyzeOptions
    status: JobStatus = "queued"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    progress: list[JobProgressMessage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    result: AnalyzeWorkflowResult | None = None
    error: str | None = None


class AnalyzeJobRegistry:
    """Small process-local job store for the local workbench."""

    def __init__(self) -> None:
        self._jobs: dict[str, AnalyzeJobRecord] = {}
        self._lock = RLock()

    def create(self, upload_path: Path, upload_filename: str, options: AnalyzeOptions) -> AnalyzeJobRecord:
        """Create and store a queued analyze job."""

        job_id = uuid4().hex
        record = AnalyzeJobRecord(
            job_id=job_id,
            upload_path=upload_path,
            upload_filename=upload_filename,
            options=options,
        )
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> AnalyzeJobRecord | None:
        """Return one job record if it exists."""

        with self._lock:
            return self._jobs.get(job_id)

    def snapshot(self, job_id: str) -> AnalyzeJobStatusResponse | None:
        """Return an immutable response snapshot for a job."""

        record = self.get(job_id)
        if record is None:
            return None
        return self._to_response(record)

    def mark_running(self, job_id: str) -> None:
        """Mark a job as running."""

        with self._lock:
            record = self._jobs[job_id]
            record.status = "running"
            record.updated_at = utc_now()

    def add_progress(self, job_id: str, message: str) -> None:
        """Append one progress message to a job."""

        normalized = str(message).strip()
        if not normalized:
            return
        with self._lock:
            record = self._jobs[job_id]
            record.progress.append(JobProgressMessage(message=normalized, timestamp=utc_now()))
            record.updated_at = utc_now()

    def add_warnings(self, job_id: str, warnings: list[str]) -> None:
        """Append unique warnings to a job."""

        normalized = [str(item).strip() for item in warnings if str(item).strip()]
        if not normalized:
            return
        with self._lock:
            record = self._jobs[job_id]
            existing = set(record.warnings)
            for warning in normalized:
                if warning not in existing:
                    record.warnings.append(warning)
                    existing.add(warning)
            record.updated_at = utc_now()

    def mark_succeeded(self, job_id: str, result: AnalyzeWorkflowResult) -> None:
        """Mark a job as succeeded with its workflow result."""

        with self._lock:
            record = self._jobs[job_id]
            record.status = "succeeded"
            record.result = result
            record.error = None
            record.updated_at = utc_now()
        self.add_warnings(job_id, result.warnings)

    def mark_failed(self, job_id: str, error: Exception) -> None:
        """Mark a job as failed with a readable error."""

        with self._lock:
            record = self._jobs[job_id]
            record.status = "failed"
            record.error = f"{type(error).__name__}: {error}"
            record.updated_at = utc_now()

    def _to_response(self, record: AnalyzeJobRecord) -> AnalyzeJobStatusResponse:
        return AnalyzeJobStatusResponse(
            job_id=record.job_id,
            status=record.status,
            upload_filename=record.upload_filename,
            created_at=record.created_at,
            updated_at=record.updated_at,
            progress=list(record.progress),
            warnings=list(record.warnings),
            result=record.result,
            error=record.error,
        )
