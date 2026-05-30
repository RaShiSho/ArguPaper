import { FileText, Library, Search } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { fetchPaperDetail, fetchPapers } from "../api";
import { MarkdownPanel } from "../components/MarkdownPanel";
import type { PaperDetailResponse, PaperRecord } from "../types";

type DetailTab = "report" | "markdown";

export function LibraryPage(): JSX.Element {
  const [query, setQuery] = useState("");
  const [records, setRecords] = useState<PaperRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<PaperDetailResponse | null>(null);
  const [tab, setTab] = useState<DetailTab>("report");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadRecords("");
  }, []);

  async function loadRecords(nextQuery: string): Promise<void> {
    setLoading(true);
    setError("");
    try {
      const response = await fetchPapers(nextQuery);
      setRecords(response.records);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await loadRecords(query);
  }

  async function openDetail(record: PaperRecord): Promise<void> {
    const paperId = String(record.paper_id ?? "");
    if (!paperId) {
      return;
    }
    setSelectedId(paperId);
    setDetailLoading(true);
    setError("");
    try {
      const response = await fetchPaperDetail(paperId);
      setDetail(response);
      setTab("report");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <section className="view-stack">
      <div className="toolbar">
        <div>
          <h1>Paper Library</h1>
          <p>Browse records saved by the existing PaperStore.</p>
        </div>
      </div>

      <form className="tool-panel library-search" onSubmit={handleSearch}>
        <label className="field wide-field">
          Query
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <button className="primary-button" type="submit" disabled={loading}>
          <Search size={18} />
          {loading ? "Loading" : "Filter"}
        </button>
      </form>

      {error && <div className="error-panel">{error}</div>}

      <div className="library-layout">
        <div className="record-list">
          {records.length === 0 ? (
            <div className="empty-state">
              <Library size={16} />
              No saved papers found.
            </div>
          ) : (
            records.map((record) => {
              const paperId = String(record.paper_id ?? "");
              const libraryStatus = record.library_status ?? "analyzed";
              return (
                <button
                  className={`record-row ${paperId === selectedId ? "selected" : ""}`}
                  key={paperId || String(record.title)}
                  onClick={() => void openDetail(record)}
                  type="button"
                >
                  <FileText size={18} />
                  <span>
                    <strong>{record.title || "Untitled"}</strong>
                    <small>{paperId || "N/A"}</small>
                    <small className={`library-status library-status-${libraryStatus}`}>{libraryStatus}</small>
                  </span>
                  <time>{record.updated_at || "N/A"}</time>
                </button>
              );
            })
          )}
        </div>

        <div className="detail-pane">
          {detailLoading && <div className="empty-state">Loading record detail.</div>}
          {!detailLoading && !detail && <div className="empty-state">Select a saved paper to inspect it.</div>}
          {!detailLoading && detail && (
            <>
              <div className="metadata-grid">
                <div>
                  <span>Title</span>
                  <strong>{String(detail.metadata.title ?? "Untitled")}</strong>
                </div>
                <div>
                  <span>Paper ID</span>
                  <strong>{String(detail.metadata.paper_id ?? selectedId)}</strong>
                </div>
                <div>
                  <span>Status</span>
                  <strong>{String(detail.metadata.library_status ?? "analyzed")}</strong>
                </div>
                <div>
                  <span>Source</span>
                  <strong>{String(detail.metadata.source ?? "N/A")}</strong>
                </div>
                <div>
                  <span>From cache</span>
                  <strong>{detail.metadata.from_cache ? "yes" : "no"}</strong>
                </div>
              </div>

              <div className="summary-grid">
                {["problem", "method", "experiment", "conclusion"].map((key) => (
                  <div key={key}>
                    <span>{key}</span>
                    <p>{String(detail.abstract[key] ?? "N/A")}</p>
                  </div>
                ))}
              </div>

              <div className="tab-row">
                <button className={tab === "report" ? "active" : ""} onClick={() => setTab("report")} type="button">
                  Report
                </button>
                <button
                  className={tab === "markdown" ? "active" : ""}
                  onClick={() => setTab("markdown")}
                  type="button"
                >
                  Paper Markdown
                </button>
              </div>
              <MarkdownPanel markdown={tab === "report" ? detail.report : detail.markdown} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}
