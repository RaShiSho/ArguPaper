import { MarkdownPanel } from "./MarkdownPanel";
import { StatusBadge } from "./StatusBadge";
import { Warnings } from "./Warnings";
import type {
  AnalyzeWorkflowResult,
  ConvertWorkflowResult,
  CourtWorkflowResult,
  RAGDeleteResult,
  RAGIndexResult,
  WorkflowJobStatusResponse
} from "../types";

export type WorkflowJobResult =
  | AnalyzeWorkflowResult
  | ConvertWorkflowResult
  | CourtWorkflowResult
  | RAGIndexResult
  | RAGDeleteResult;

interface WorkflowJobPanelProps {
  job: WorkflowJobStatusResponse<WorkflowJobResult>;
}

export function WorkflowJobPanel({ job }: WorkflowJobPanelProps): JSX.Element {
  const result = job.result;
  const conversion = result && "conversion" in result ? result.conversion : null;
  const markdown =
    result && "report_markdown" in result
      ? result.report_markdown
      : conversion?.markdown
        ? conversion.markdown
        : "";

  return (
    <>
      <div className="job-header">
        <div>
          <span className="section-label">{job.kind}</span>
          <h2>{job.label}</h2>
        </div>
        <StatusBadge status={job.status} />
      </div>
      {job.error && <div className="error-panel">{job.error}</div>}
      <Warnings warnings={job.warnings} />
      <div className="timeline">
        {job.progress.length === 0 ? (
          <div className="empty-state">Waiting for workflow progress.</div>
        ) : (
          job.progress.map((item) => (
            <div className="timeline-row" key={`${item.timestamp}-${item.message}`}>
              <time>{new Date(item.timestamp).toLocaleTimeString()}</time>
              <span>{item.message}</span>
            </div>
          ))
        )}
      </div>
      {result && <WorkflowResultSummary result={result} />}
      {markdown && <MarkdownPanel markdown={markdown} />}
    </>
  );
}

function WorkflowResultSummary({ result }: { result: WorkflowJobResult }): JSX.Element {
  if ("summary" in result && result.summary) {
    return (
      <div className="metrics-row">
        <div>
          <span>Total</span>
          <strong>{result.summary.total_entries}</strong>
        </div>
        <div>
          <span>Succeeded</span>
          <strong>{result.summary.success}</strong>
        </div>
        <div>
          <span>Cache hits</span>
          <strong>{result.summary.cache_hits}</strong>
        </div>
        <div>
          <span>Failed</span>
          <strong>{result.summary.failed}</strong>
        </div>
      </div>
    );
  }

  if ("conversion" in result && result.conversion) {
    return (
      <div className="metrics-row">
        <div>
          <span>Cache key</span>
          <strong>{result.conversion.cache_key}</strong>
        </div>
        <div>
          <span>Cache</span>
          <strong>{result.conversion.from_cache ? "yes" : "no"}</strong>
        </div>
        <div>
          <span>Cache path</span>
          <strong>{result.cache_path ?? "N/A"}</strong>
        </div>
        <div>
          <span>Output</span>
          <strong>{result.output_path ?? "N/A"}</strong>
        </div>
      </div>
    );
  }

  if ("chunk_count" in result) {
    return (
      <div className="metrics-row">
        <div>
          <span>Paper ID</span>
          <strong>{result.paper_id}</strong>
        </div>
        <div>
          <span>Chunks</span>
          <strong>{result.chunk_count}</strong>
        </div>
        <div>
          <span>Embedding dim</span>
          <strong>{result.embedding_dim ?? "N/A"}</strong>
        </div>
        <div>
          <span>Dry run</span>
          <strong>{result.dry_run ? "yes" : "no"}</strong>
        </div>
      </div>
    );
  }

  if ("deleted_count" in result) {
    return (
      <div className="metrics-row">
        <div>
          <span>Paper ID</span>
          <strong>{result.paper_id}</strong>
        </div>
        <div>
          <span>Deleted chunks</span>
          <strong>{result.deleted_count ?? "unknown"}</strong>
        </div>
        <div>
          <span>Run log</span>
          <strong>{result.run_log_path ?? "N/A"}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>complete</strong>
        </div>
      </div>
    );
  }

  if ("paper_id" in result) {
    return (
      <div className="metrics-row">
        <div>
          <span>Paper ID</span>
          <strong>{result.paper_id}</strong>
        </div>
        <div>
          <span>Cache</span>
          <strong>{"from_cache" in result ? (result.from_cache ? "yes" : "no") : "N/A"}</strong>
        </div>
        <div>
          <span>Report</span>
          <strong>{"saved_report_path" in result ? (result.saved_report_path ?? "N/A") : "N/A"}</strong>
        </div>
        <div>
          <span>Retrieval</span>
          <strong>
            {"supplementary_search_used" in result
              ? result.supplementary_search_used
                ? "used"
                : "not used"
              : "N/A"}
          </strong>
        </div>
      </div>
    );
  }

  return <div className="empty-state">Workflow completed.</div>;
}
