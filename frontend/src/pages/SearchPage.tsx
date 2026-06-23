import { ExternalLink, Search } from "lucide-react";
import { FormEvent, useState } from "react";

import { searchPapers } from "../api";
import { Warnings } from "../components/Warnings";
import type { SearchAgentResult, SearchSource } from "../types";

const sources: { value: SearchSource; label: string }[] = [
  { value: "both", label: "All configured" },
  { value: "semantic_scholar", label: "Semantic Scholar" },
  { value: "arxiv", label: "arXiv" },
  { value: "google_scholar", label: "Google Scholar" },
  { value: "serpapi", label: "SerpApi" }
];

export function SearchPage(): JSX.Element {
  const [query, setQuery] = useState("retrieval augmented generation");
  const [limit, setLimit] = useState(10);
  const [source, setSource] = useState<SearchSource>("both");
  const [verbose, setVerbose] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<SearchAgentResult | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await searchPapers({ query, limit, source, verbose });
      setResult(response.result);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="view-stack">
      <div className="toolbar">
        <div>
          <h1>Search</h1>
          <p>Find external academic paper candidates through the configured retrieval sources.</p>
        </div>
      </div>

      <form className="tool-panel search-form" onSubmit={handleSubmit}>
        <label className="field wide-field">
          Query
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <label className="field small-field">
          Limit
          <input
            min={1}
            max={50}
            type="number"
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        <label className="field">
          Source
          <select value={source} onChange={(event) => setSource(event.target.value as SearchSource)}>
            {sources.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="check-field">
          <input type="checkbox" checked={verbose} onChange={(event) => setVerbose(event.target.checked)} />
          Verbose
        </label>
        <button className="primary-button" type="submit" disabled={loading}>
          <Search size={18} />
          {loading ? "Searching" : "Search"}
        </button>
      </form>

      {error && <div className="error-panel">{error}</div>}
      {!result && !error && <div className="empty-state">Submit a query to inspect external paper candidates.</div>}
      {result && (
        <>
          <Warnings warnings={result.warnings} />
          <div className="metrics-row">
            <div>
              <span>Retrieved</span>
              <strong>{result.retrieved_count}</strong>
            </div>
            <div>
              <span>Filtered</span>
              <strong>{result.filtered_count}</strong>
            </div>
            <div>
              <span>Candidate limit</span>
              <strong>{result.candidate_limit}</strong>
            </div>
            <div>
              <span>Parser</span>
              <strong>{result.parse_result.parser}</strong>
            </div>
          </div>

          {result.results.length === 0 ? (
            <div className="empty-state">Search completed but returned no papers.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Authors</th>
                    <th>Year</th>
                    <th>Venue</th>
                    <th>Citations</th>
                    <th>Source</th>
                    <th>URL</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((paper, index) => (
                    <tr key={`${paper.title}-${index}`}>
                      <td>{paper.title}</td>
                      <td>{paper.authors.slice(0, 3).join(", ") || "N/A"}</td>
                      <td>{paper.year ?? "N/A"}</td>
                      <td>{paper.venue || "N/A"}</td>
                      <td>{paper.citation_count}</td>
                      <td>{paper.source}</td>
                      <td>
                        {paper.url ? (
                          <a href={paper.url} target="_blank" rel="noreferrer" aria-label={`Open ${paper.title}`}>
                            <ExternalLink size={16} />
                          </a>
                        ) : (
                          "N/A"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="trace-panel">
            <span>Expanded queries: {result.expanded_queries.join(" | ") || "N/A"}</span>
            <span>Trace: {result.trace_dir}</span>
          </div>
        </>
      )}
    </section>
  );
}
