import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownPanelProps {
  markdown: string;
  emptyText?: string;
}

export function MarkdownPanel({ markdown, emptyText = "No Markdown available." }: MarkdownPanelProps): JSX.Element {
  if (!markdown.trim()) {
    return <div className="empty-state">{emptyText}</div>;
  }
  return (
    <article className="markdown-panel">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </article>
  );
}
