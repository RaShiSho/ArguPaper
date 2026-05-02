import { FileUp, RefreshCw } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { fetchJob, submitAnalyze } from "../api";
import { MarkdownPanel } from "../components/MarkdownPanel";
import { StatusBadge } from "../components/StatusBadge";
import { Warnings } from "../components/Warnings";
import type { AnalyzeJobStatusResponse } from "../types";

const finalStatuses = new Set(["succeeded", "failed"]);

export function AnalyzePage(): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [rounds, setRounds] = useState(3);
  const [forceReconvert, setForceReconvert] = useState(false);
  const [verbose, setVerbose] = useState(false);
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<AnalyzeJobStatusResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId || (job && finalStatuses.has(job.status))) {
      return undefined;
    }

    let cancelled = false;

    async function loadJob(): Promise<void> {
      try {
        const nextJob = await fetchJob(jobId);
        if (!cancelled) {
          setJob(nextJob);
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!file) {
      setError("Select a PDF before starting analysis.");
      return;
    }
    setSubmitting(true);
    setError("");
    setJob(null);
    try {
      const response = await submitAnalyze({ file, rounds, forceReconvert, verbose });
      setJobId(response.job_id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="view-stack">
      <div className="toolbar">
        <div>
          <h1>PDF Analysis</h1>
          <p>Upload a local PDF and watch the existing analyze workflow run as a background job.</p>
        </div>
      </div>

      <form className="tool-panel analyze-form" onSubmit={handleSubmit}>
        <label className="field file-field">
          PDF
          <input
            accept="application/pdf,.pdf"
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <label className="field small-field">
          Rounds
          <input
            min={1}
            max={10}
            type="number"
            value={rounds}
            onChange={(event) => setRounds(Number(event.target.value))}
          />
        </label>
        <label className="check-field">
          <input
            type="checkbox"
            checked={forceReconvert}
            onChange={(event) => setForceReconvert(event.target.checked)}
          />
          Force reconvert
        </label>
        <label className="check-field">
          <input type="checkbox" checked={verbose} onChange={(event) => setVerbose(event.target.checked)} />
          Verbose
        </label>
        <button className="primary-button" type="submit" disabled={submitting}>
          <FileUp size={18} />
          {submitting ? "Submitting" : "Start"}
        </button>
      </form>

      {error && <div className="error-panel">{error}</div>}

      {job && (
        <>
          <div className="job-header">
            <div>
              <span className="section-label">Job</span>
              <h2>{job.upload_filename}</h2>
            </div>
            <StatusBadge status={job.status} />
          </div>

          {job.error && <div className="error-panel">{job.error}</div>}
          <Warnings warnings={job.warnings} />

          <div className="timeline">
            {job.progress.length === 0 ? (
              <div className="empty-state">
                <RefreshCw size={16} />
                Waiting for workflow progress.
              </div>
            ) : (
              job.progress.map((item) => (
                <div className="timeline-row" key={`${item.timestamp}-${item.message}`}>
                  <time>{new Date(item.timestamp).toLocaleTimeString()}</time>
                  <span>{item.message}</span>
                </div>
              ))
            )}
          </div>

          {job.result && (
            <>
              <div className="metrics-row">
                <div>
                  <span>Paper ID</span>
                  <strong>{job.result.paper_id}</strong>
                </div>
                <div>
                  <span>Cache</span>
                  <strong>{job.result.from_cache ? "yes" : "no"}</strong>
                </div>
                <div>
                  <span>Supplementary retrieval</span>
                  <strong>{job.result.supplementary_search_used ? "used" : "not used"}</strong>
                </div>
              </div>
              <MarkdownPanel markdown={job.result.report_markdown} />
            </>
          )}
        </>
      )}
    </section>
  );
}
