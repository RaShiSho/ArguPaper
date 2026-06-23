import { Database, RefreshCw, Search, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";

import { fetchRAGStatus, searchRAG, submitRAGDelete, submitRAGIndex } from "../api";
import { MarkdownPanel } from "../components/MarkdownPanel";
import { Warnings } from "../components/Warnings";
import { WorkflowJobPanel, type WorkflowJobResult } from "../components/WorkflowJobPanel";
import { useWorkflowJob } from "../hooks/useWorkflowJob";
import type { RAGSearchResult, RAGStatusResult } from "../types";

export function RAGPage(): JSX.Element {
  const [status, setStatus] = useState<RAGStatusResult | null>(null);
  const [paperId, setPaperId] = useState("");
  const [dryRun, setDryRun] = useState(false);
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [sectionType, setSectionType] = useState("");
  const [scoreThreshold, setScoreThreshold] = useState("");
  const [contextMaxChars, setContextMaxChars] = useState(12000);
  const [searchResult, setSearchResult] = useState<RAGSearchResult | null>(null);
  const [loading, setLoading] = useState("");
  const { job, error, setError, acceptJob } = useWorkflowJob<WorkflowJobResult>();

  async function loadStatus(): Promise<void> {
    setLoading("status");
    setError("");
    try {
      setStatus(await fetchRAGStatus());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading("");
    }
  }

  async function handleIndex(): Promise<void> {
    setLoading("index");
    setError("");
    try {
      const response = await submitRAGIndex({ paperId, dryRun });
      acceptJob(response.job_id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading("");
    }
  }

  async function handleDelete(): Promise<void> {
    setLoading("delete");
    setError("");
    try {
      const response = await submitRAGDelete({ paperId });
      acceptJob(response.job_id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading("");
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading("search");
    setError("");
    try {
      setSearchResult(await searchRAG({ content: query, paperId, topK, sectionType, scoreThreshold, contextMaxChars }));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading("");
    }
  }

  return (
    <section className="view-stack">
      <div className="toolbar">
        <div>
          <h1>RAG</h1>
          <p>Inspect, index, delete, and search local paper chunks in the RAG system.</p>
        </div>
      </div>

      <div className="tool-panel workflow-form">
        <label className="field wide-field">
          Paper ID
          <input value={paperId} onChange={(event) => setPaperId(event.target.value)} />
        </label>
        <label className="check-field">
          <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
          Dry run
        </label>
        <button className="primary-button" type="button" onClick={() => void loadStatus()} disabled={loading === "status"}>
          <Database size={18} />
          Status
        </button>
        <button className="primary-button" type="button" onClick={() => void handleIndex()} disabled={loading === "index"}>
          <RefreshCw size={18} />
          Index
        </button>
        <button className="primary-button danger-button" type="button" onClick={() => void handleDelete()} disabled={loading === "delete"}>
          <Trash2 size={18} />
          Delete
        </button>
      </div>

      {status && (
        <div className="metrics-row">
          <div>
            <span>Enabled</span>
            <strong>{status.rag_enabled ? "yes" : "no"}</strong>
          </div>
          <div>
            <span>Embedding</span>
            <strong>{status.ollama_embed_model}</strong>
          </div>
          <div>
            <span>Milvus</span>
            <strong>{status.milvus_collection}</strong>
          </div>
          <div>
            <span>Top K</span>
            <strong>{status.top_k}</strong>
          </div>
        </div>
      )}

      <form className="tool-panel workflow-form" onSubmit={handleSearch}>
        <label className="field wide-field">
          Search query
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <label className="field small-field">
          Top K
          <input min={1} max={100} type="number" value={topK} onChange={(event) => setTopK(Number(event.target.value))} />
        </label>
        <label className="field wide-field">
          Section
          <input value={sectionType} onChange={(event) => setSectionType(event.target.value)} />
        </label>
        <label className="field small-field">
          Score
          <input value={scoreThreshold} onChange={(event) => setScoreThreshold(event.target.value)} />
        </label>
        <label className="field small-field">
          Context
          <input
            min={1000}
            max={100000}
            type="number"
            value={contextMaxChars}
            onChange={(event) => setContextMaxChars(Number(event.target.value))}
          />
        </label>
        <button className="primary-button" type="submit" disabled={loading === "search"}>
          <Search size={18} />
          {loading === "search" ? "Searching" : "Search RAG"}
        </button>
      </form>

      {error && <div className="error-panel">{error}</div>}
      {job && <WorkflowJobPanel job={job} />}

      {searchResult && (
        <>
          <Warnings warnings={searchResult.warnings} />
          <div className="metrics-row">
            <div>
              <span>Chunks</span>
              <strong>{searchResult.chunks.length}</strong>
            </div>
            <div>
              <span>Top K</span>
              <strong>{searchResult.top_k}</strong>
            </div>
            <div>
              <span>Paper filter</span>
              <strong>{searchResult.paper_id ?? "all"}</strong>
            </div>
            <div>
              <span>Run log</span>
              <strong>{searchResult.run_log_path ?? "N/A"}</strong>
            </div>
          </div>
          {searchResult.chunks.length === 0 ? (
            <div className="empty-state">No RAG chunks matched the query.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Chunk</th>
                    <th>Paper</th>
                    <th>Section</th>
                    <th>Page</th>
                    <th>Score</th>
                    <th>Preview</th>
                  </tr>
                </thead>
                <tbody>
                  {searchResult.chunks.map((chunk) => (
                    <tr key={chunk.chunk_id}>
                      <td>{chunk.chunk_id}</td>
                      <td>{chunk.paper_id}</td>
                      <td>{chunk.section || chunk.section_type || "unknown"}</td>
                      <td>{pageLabel(chunk.page_start, chunk.page_end)}</td>
                      <td>{chunk.score.toFixed(4)}</td>
                      <td>{chunk.text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {searchResult.context && <MarkdownPanel markdown={`\`\`\`\n${searchResult.context}\n\`\`\``} />}
        </>
      )}
    </section>
  );
}

function pageLabel(start?: number | null, end?: number | null): string {
  if (start == null && end == null) {
    return "unknown";
  }
  if (end == null || end === start) {
    return String(start);
  }
  if (start == null) {
    return String(end);
  }
  return `${start}-${end}`;
}
