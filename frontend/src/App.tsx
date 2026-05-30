import { Activity, FileSearch, FileText, Library, Server } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchConfigStatus } from "./api";
import { AnalyzePage } from "./pages/AnalyzePage";
import { LibraryPage } from "./pages/LibraryPage";
import { SearchPage } from "./pages/SearchPage";
import type { ConfigStatusResponse } from "./types";

type View = "search" | "analyze" | "library";

const navItems: { id: View; label: string; icon: JSX.Element }[] = [
  { id: "search", label: "Search", icon: <FileSearch size={18} /> },
  { id: "analyze", label: "Analyze", icon: <FileText size={18} /> },
  { id: "library", label: "Library", icon: <Library size={18} /> }
];

export function App(): JSX.Element {
  const [activeView, setActiveView] = useState<View>("search");
  const [config, setConfig] = useState<ConfigStatusResponse | null>(null);
  const [configError, setConfigError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadConfig(): Promise<void> {
      try {
        const response = await fetchConfigStatus();
        if (!cancelled) {
          setConfig(response);
          setConfigError("");
        }
      } catch (exc) {
        if (!cancelled) {
          setConfigError(exc instanceof Error ? exc.message : String(exc));
        }
      }
    }
    void loadConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Activity size={24} />
          <div>
            <strong>ArguPaper</strong>
            <span>Local Workbench</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Workbench views">
          {navItems.map((item) => (
            <button
              className={activeView === item.id ? "active" : ""}
              key={item.id}
              onClick={() => setActiveView(item.id)}
              type="button"
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        <div className="config-panel">
          <div className="section-label">
            <Server size={16} />
            Config
          </div>
          {configError && <div className="small-error">{configError}</div>}
          {config && (
            <dl>
              <div>
                <dt>MinerU</dt>
                <dd>{config.mineru_api_configured ? "configured" : "missing"}</dd>
              </div>
              <div>
                <dt>Semantic Scholar</dt>
                <dd>{config.semantic_scholar_configured ? "configured" : "optional"}</dd>
              </div>
              <div>
                <dt>SerpApi</dt>
                <dd>{config.serpapi_configured ? "configured" : "optional"}</dd>
              </div>
              <div>
                <dt>Retrieval loop</dt>
                <dd>{config.analyze_retrieval_loop_enabled ? "on" : "off"}</dd>
              </div>
              <div>
                <dt>Web logs</dt>
                <dd>{config.web_log_path}</dd>
              </div>
            </dl>
          )}
        </div>
      </aside>

      <main className="main-panel">
        {activeView === "search" && <SearchPage />}
        {activeView === "analyze" && <AnalyzePage />}
        {activeView === "library" && <LibraryPage />}
      </main>
    </div>
  );
}
