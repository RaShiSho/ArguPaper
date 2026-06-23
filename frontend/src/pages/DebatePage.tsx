import { FileUp, RefreshCw, Swords } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { fetchJob, submitAnalyze, submitDebate } from "../api";
import { MarkdownPanel } from "../components/MarkdownPanel";
import { StatusBadge } from "../components/StatusBadge";
import { Warnings } from "../components/Warnings";
import { WorkflowJobPanel, type WorkflowJobResult } from "../components/WorkflowJobPanel";
import { useWorkflowJob } from "../hooks/useWorkflowJob";
import type { AnalyzeJobStatusResponse } from "../types";

type DebateMode = "upload" | "paper";

const finalStatuses = new Set(["succeeded", "failed"]);

export function DebatePage(): JSX.Element {
  const [mode, setMode] = useState<DebateMode>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [uploadRounds, setUploadRounds] = useState(3);
  const [forceReconvert, setForceReconvert] = useState(false);
  const [uploadVerbose, setUploadVerbose] = useState(false);
  const [uploadJobId, setUploadJobId] = useState("");
  const [uploadJob, setUploadJob] = useState<AnalyzeJobStatusResponse | null>(null);
  const [uploadSubmitting, setUploadSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [paper, setPaper] = useState("");
  const [paperRounds, setPaperRounds] = useState(3);
  const [outputPath, setOutputPath] = useState("");
  const [saveReport, setSaveReport] = useState(false);
  const [paperForce, setPaperForce] = useState(false);
  const [paperVerbose, setPaperVerbose] = useState(false);
  const [paperSubmitting, setPaperSubmitting] = useState(false);
  const paperJob = useWorkflowJob<WorkflowJobResult>();

  useEffect(() => {
    if (!uploadJobId || (uploadJob && finalStatuses.has(uploadJob.status))) {
      return undefined;
    }

    let cancelled = false;

    async function loadJob(): Promise<void> {
      try {
        const nextJob = await fetchJob(uploadJobId);
        if (!cancelled) {
          setUploadJob(nextJob);
          setUploadError("");
        }
      } catch (exc) {
        if (!cancelled) {
          setUploadError(exc instanceof Error ? exc.message : String(exc));
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
  }, [uploadJobId, uploadJob?.status]);

  async function handleUploadSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!file) {
      setUploadError("Select a PDF before starting debate.");
      return;
    }
    setUploadSubmitting(true);
    setUploadError("");
    setUploadJob(null);
    try {
      const response = await submitAnalyze({
        file,
        rounds: uploadRounds,
        forceReconvert,
        verbose: uploadVerbose
      });
      setUploadJobId(response.job_id);
    } catch (exc) {
      setUploadError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setUploadSubmitting(false);
    }
  }

  async function handlePaperSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setPaperSubmitting(true);
    paperJob.setError("");
    try {
      const response = await submitDebate({
        paper,
        rounds: paperRounds,
        outputPath,
        saveReport,
        force: paperForce,
        verbose: paperVerbose
      });
      paperJob.acceptJob(response.job_id);
    } catch (exc) {
      paperJob.setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setPaperSubmitting(false);
    }
  }

  return (
    <section className="view-stack">
      <div className="toolbar">
        <div>
          <h1>Debate</h1>
          <p>Run multi-agent debate analysis from an uploaded PDF or an existing paper record.</p>
        </div>
      </div>

      <div className="tab-row">
        <button className={mode === "upload" ? "active" : ""} onClick={() => setMode("upload")} type="button">
          Upload PDF
        </button>
        <button className={mode === "paper" ? "active" : ""} onClick={() => setMode("paper")} type="button">
          Saved paper / path
        </button>
      </div>

      {mode === "upload" && (
        <>
          <form className="tool-panel workflow-form" onSubmit={handleUploadSubmit}>
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
                value={uploadRounds}
                onChange={(event) => setUploadRounds(Number(event.target.value))}
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
              <input type="checkbox" checked={uploadVerbose} onChange={(event) => setUploadVerbose(event.target.checked)} />
              Verbose
            </label>
            <button className="primary-button" type="submit" disabled={uploadSubmitting}>
              <FileUp size={18} />
              {uploadSubmitting ? "Submitting" : "Run Debate"}
            </button>
          </form>
          {uploadError && <div className="error-panel">{uploadError}</div>}
          {!uploadJob && !uploadError && <div className="empty-state">Upload a PDF to start a debate job.</div>}
          {uploadJob && <AnalyzeJobPanel job={uploadJob} />}
        </>
      )}

      {mode === "paper" && (
        <>
          <form className="tool-panel workflow-form" onSubmit={handlePaperSubmit}>
            <label className="field wide-field">
              Paper ID, name, or PDF path
              <input value={paper} onChange={(event) => setPaper(event.target.value)} />
            </label>
            <label className="field small-field">
              Rounds
              <input min={1} max={20} type="number" value={paperRounds} onChange={(event) => setPaperRounds(Number(event.target.value))} />
            </label>
            <label className="field wide-field">
              Output
              <input value={outputPath} onChange={(event) => setOutputPath(event.target.value)} />
            </label>
            <label className="check-field">
              <input type="checkbox" checked={saveReport} onChange={(event) => setSaveReport(event.target.checked)} />
              Save report
            </label>
            <label className="check-field">
              <input type="checkbox" checked={paperForce} onChange={(event) => setPaperForce(event.target.checked)} />
              Force
            </label>
            <label className="check-field">
              <input type="checkbox" checked={paperVerbose} onChange={(event) => setPaperVerbose(event.target.checked)} />
              Verbose
            </label>
            <button className="primary-button" type="submit" disabled={paperSubmitting}>
              <Swords size={18} />
              {paperSubmitting ? "Submitting" : "Run Debate"}
            </button>
          </form>
          {paperJob.error && <div className="error-panel">{paperJob.error}</div>}
          {!paperJob.job && !paperJob.error && (
            <div className="empty-state">Run debate for a converted paper name, saved paper ID, or local PDF path.</div>
          )}
          {paperJob.job && <WorkflowJobPanel job={paperJob.job} />}
        </>
      )}
    </section>
  );
}

function AnalyzeJobPanel({ job }: { job: AnalyzeJobStatusResponse }): JSX.Element {
  return (
    <>
      <div className="job-header">
        <div>
          <span className="section-label">Debate job</span>
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
              <span>Retrieval</span>
              <strong>{job.result.supplementary_search_used ? "used" : "not used"}</strong>
            </div>
            <div>
              <span>Report</span>
              <strong>{job.result.saved_report_path ?? "N/A"}</strong>
            </div>
          </div>
          <MarkdownPanel markdown={job.result.report_markdown} />
        </>
      )}
    </>
  );
}
