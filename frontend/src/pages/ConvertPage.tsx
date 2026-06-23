import { FileUp } from "lucide-react";
import { FormEvent, useState } from "react";

import { submitConvertPath, submitConvertUpload } from "../api";
import { WorkflowJobPanel, type WorkflowJobResult } from "../components/WorkflowJobPanel";
import { useWorkflowJob } from "../hooks/useWorkflowJob";

export function ConvertPage(): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [pdfPath, setPdfPath] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [force, setForce] = useState(false);
  const [loading, setLoading] = useState(false);
  const { job, error, setError, acceptJob } = useWorkflowJob<WorkflowJobResult>();

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = file
        ? await submitConvertUpload({ file, outputPath, force })
        : await submitConvertPath({ pdfPath, folderPath, outputPath, force });
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
          <h1>Convert</h1>
          <p>Convert local PDFs to cached Markdown and save converted papers into the local library.</p>
        </div>
      </div>

      <form className="tool-panel workflow-form" onSubmit={handleSubmit}>
        <label className="field file-field">
          Upload PDF
          <input
            accept="application/pdf,.pdf"
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <label className="field wide-field">
          PDF path
          <input value={pdfPath} onChange={(event) => setPdfPath(event.target.value)} disabled={Boolean(file)} />
        </label>
        <label className="field wide-field">
          Folder path
          <input value={folderPath} onChange={(event) => setFolderPath(event.target.value)} disabled={Boolean(file)} />
        </label>
        <label className="field wide-field">
          Output
          <input value={outputPath} onChange={(event) => setOutputPath(event.target.value)} />
        </label>
        <label className="check-field">
          <input type="checkbox" checked={force} onChange={(event) => setForce(event.target.checked)} />
          Force
        </label>
        <button className="primary-button" type="submit" disabled={loading}>
          <FileUp size={18} />
          {loading ? "Submitting" : "Convert"}
        </button>
      </form>

      {error && <div className="error-panel">{error}</div>}
      {!job && !error && <div className="empty-state">Submit a PDF or folder conversion to see progress here.</div>}
      {job && <WorkflowJobPanel job={job} />}
    </section>
  );
}
