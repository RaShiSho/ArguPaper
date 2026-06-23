import { Bot, Send } from "lucide-react";
import type { Dispatch, FormEvent, SetStateAction } from "react";

import { createChatSession, sendChatTurn } from "../api";
import { MarkdownPanel } from "../components/MarkdownPanel";
import { Warnings } from "../components/Warnings";
import type { ChatTurnResponse } from "../types";

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  result?: ChatTurnResponse;
}

interface ChatPageProps {
  sessionId: string;
  setSessionId: Dispatch<SetStateAction<string>>;
  message: string;
  setMessage: Dispatch<SetStateAction<string>>;
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  loading: boolean;
  setLoading: Dispatch<SetStateAction<boolean>>;
  error: string;
  setError: Dispatch<SetStateAction<string>>;
}

export function ChatPage({
  sessionId,
  setSessionId,
  message,
  setMessage,
  messages,
  setMessages,
  loading,
  setLoading,
  error,
  setError
}: ChatPageProps): JSX.Element {

  async function ensureSession(): Promise<string> {
    if (sessionId) {
      return sessionId;
    }
    const session = await createChatSession();
    setSessionId(session.session_id);
    return session.session_id;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    setMessages((items) => [...items, { role: "user", text: trimmed }]);
    try {
      const activeSession = await ensureSession();
      const response = await sendChatTurn(activeSession, trimmed);
      setMessages((items) => [...items, { role: "assistant", text: response.response, result: response }]);
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
          <h1>Research Chat</h1>
          <p>Use the same stateful chat agent commands and natural-language runtime as the CLI.</p>
        </div>
        {sessionId && <span className="session-pill">{sessionId}</span>}
      </div>

      {error && <div className="error-panel">{error}</div>}

      <div className="chat-panel">
        {messages.length === 0 ? (
          <div className="empty-state">
            <Bot size={16} />
            Start a chat session.
          </div>
        ) : (
          messages.map((item, index) => (
            <div className={`chat-message chat-${item.role}`} key={`${item.role}-${index}`}>
              <strong>{item.role === "user" ? "You" : "ArguPaper"}</strong>
              {item.role === "assistant" ? <MarkdownPanel markdown={item.text} /> : <p>{item.text}</p>}
              {item.result?.selected_paper && (
                <small>
                  Selected: {item.result.selected_paper.paper_id} | {item.result.selected_paper.title}
                </small>
              )}
              {item.result?.warnings && <Warnings warnings={item.result.warnings} />}
              {item.result?.log_path && <small>Log: {item.result.log_path}</small>}
            </div>
          ))
        )}
      </div>

      <form className="tool-panel chat-form" onSubmit={handleSubmit}>
        <label className="field wide-field">
          Message
          <input value={message} onChange={(event) => setMessage(event.target.value)} />
        </label>
        <button className="primary-button" type="submit" disabled={loading}>
          <Send size={18} />
          {loading ? "Running" : "Send"}
        </button>
      </form>
    </section>
  );
}
