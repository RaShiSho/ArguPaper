import { useEffect, useState } from "react";

import { fetchWorkflowJob } from "../api";
import type { WorkflowJobStatusResponse } from "../types";

const finalStatuses = new Set(["succeeded", "failed"]);

export function useWorkflowJob<T>() {
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<WorkflowJobStatusResponse<T> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId || (job && finalStatuses.has(job.status))) {
      return undefined;
    }

    let cancelled = false;

    async function loadJob(): Promise<void> {
      try {
        const response = await fetchWorkflowJob<T>(jobId);
        if (!cancelled) {
          setJob(response);
          setError("");
        }
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : String(exc));
        }
      }
    }

    void loadJob();
    const interval = window.setInterval(() => {
      void loadJob();
    }, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [jobId, job?.status]);

  function acceptJob(nextJobId: string): void {
    setJobId(nextJobId);
    setJob(null);
    setError("");
  }

  return { job, error, setError, acceptJob };
}
