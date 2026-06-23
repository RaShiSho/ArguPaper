import { Activity, Bot, Database, FileSearch, FileUp, Gavel, Library, Server, Swords } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchConfigStatus } from "./api";
import { ChatPage } from "./pages/ChatPage";
import type { ChatMessage } from "./pages/ChatPage";
import { ConvertPage } from "./pages/ConvertPage";
import { CourtPage } from "./pages/CourtPage";
import { DebatePage } from "./pages/DebatePage";
import { LibraryPage } from "./pages/LibraryPage";
import { RAGPage } from "./pages/RAGPage";
import { SearchPage } from "./pages/SearchPage";
import type { ConfigStatusResponse } from "./types";

type View = "search" | "convert" | "debate" | "court" | "rag" | "chat" | "library";

const navItems: { id: View; label: string; icon: JSX.Element }[] = [
  { id: "search", label: "Search", icon: <FileSearch size={18} /> },
  { id: "convert", label: "Convert", icon: <FileUp size={18} /> },
  { id: "debate", label: "Debate", icon: <Swords size={18} /> },
  { id: "court", label: "Court", icon: <Gavel size={18} /> },
  { id: "rag", label: "RAG", icon: <Database size={18} /> },
  { id: "chat", label: "Chat", icon: <Bot size={18} /> },
  { id: "library", label: "Library", icon: <Library size={18} /> }
];

export function App(): JSX.Element {
  const [activeView, setActiveView] = useState<View>("search");
  const [config, setConfig] = useState<ConfigStatusResponse | null>(null);
  const [configError, setConfigError] = useState("");
  const [chatSessionId, setChatSessionId] = useState("");
  const [chatMessage, setChatMessage] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");

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
                <dt>Logs</dt>
                <dd>{config.log_path}</dd>
              </div>
            </dl>
          )}
        </div>
      </aside>

      <main className="main-panel">
        {activeView === "search" && <SearchPage />}
        {activeView === "convert" && <ConvertPage />}
        {activeView === "debate" && <DebatePage />}
        {activeView === "court" && <CourtPage />}
        {activeView === "rag" && <RAGPage />}
        {activeView === "chat" && (
          <ChatPage
            sessionId={chatSessionId}
            setSessionId={setChatSessionId}
            message={chatMessage}
            setMessage={setChatMessage}
            messages={chatMessages}
            setMessages={setChatMessages}
            loading={chatLoading}
            setLoading={setChatLoading}
            error={chatError}
            setError={setChatError}
          />
        )}
        {activeView === "library" && <LibraryPage />}
      </main>
    </div>
  );
}
