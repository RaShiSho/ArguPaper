import { AlertTriangle } from "lucide-react";

interface WarningsProps {
  warnings: string[];
}

export function Warnings({ warnings }: WarningsProps): JSX.Element | null {
  const visible = warnings.filter((item) => item.trim());
  if (visible.length === 0) {
    return null;
  }
  return (
    <div className="warning-list">
      <div className="section-label">
        <AlertTriangle size={16} />
        Warnings
      </div>
      {visible.map((warning) => (
        <div className="warning-item" key={warning}>
          {warning}
        </div>
      ))}
    </div>
  );
}
