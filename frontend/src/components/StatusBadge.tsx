import type { JobStatus } from "../types";

interface StatusBadgeProps {
  status: JobStatus;
}

const labels: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed"
};

export function StatusBadge({ status }: StatusBadgeProps): JSX.Element {
  return <span className={`status-badge status-${status}`}>{labels[status]}</span>;
}
