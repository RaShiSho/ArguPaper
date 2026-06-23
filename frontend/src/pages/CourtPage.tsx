import { Gavel } from "lucide-react";
import { FormEvent, useState } from "react";

import { submitCourt } from "../api";
import { WorkflowJobPanel, type WorkflowJobResult } from "../components/WorkflowJobPanel";
import { useWorkflowJob } from "../hooks/useWorkflowJob";

export function CourtPage(): JSX.Element {
  const [paperId, setPaperId] = useState("");
  const [rounds, setRounds] = useState(2);
  const [outputPath, setOutputPath] = useState("");
  const [verbose, setVerbose] = useState(false);
  const [loading, setLoading] = useState(false);
  const { job, error, setError, acceptJob } = useWorkflowJob<WorkflowJobResult>();

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await submitCourt({ paperId, rounds, outputPath, verbose });
      acceptJob(response.job_id);
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
          <h1>Court</h1>
          <p>Run claim-level adversarial review for a saved paper record.</p>
        </div>
      </div>

      <form className="tool-panel workflow-form" onSubmit={handleSubmit}>
        <label className="field wide-field">
          Paper ID
          <input value={paperId} onChange={(event) => setPaperId(event.target.value)} />
        </label>
        <label className="field small-field">
          Rounds
          <input min={1} max={20} type="number" value={rounds} onChange={(event) => setRounds(Number(event.target.value))} />
        </label>
        <label className="field wide-field">
          Output
          <input value={outputPath} onChange={(event) => setOutputPath(event.target.value)} />
        </label>
        <label className="check-field">
          <input type="checkbox" checked={verbose} onChange={(event) => setVerbose(event.target.checked)} />
          Verbose
        </label>
        <button className="primary-button" type="submit" disabled={loading}>
          <Gavel size={18} />
          {loading ? "Submitting" : "Run Court"}
        </button>
      </form>

      {error && <div className="error-panel">{error}</div>}
      {!job && !error && <div className="empty-state">Submit a saved paper ID to review critical claims.</div>}
      {job && <WorkflowJobPanel job={job} />}
    </section>
  );
}
