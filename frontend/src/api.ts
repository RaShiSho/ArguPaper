import type {
  AnalyzeJobStatusResponse,
  AnalyzeSubmitResponse,
  ChatSessionResponse,
  ChatTurnResponse,
  ConfigStatusResponse,
  PaperDetailResponse,
  PaperListResponse,
  RAGSearchResult,
  RAGStatusResult,
  SearchResponse,
  SearchSource,
  WorkflowJobStatusResponse,
  WorkflowSubmitResponse
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Keep the HTTP status text fallback.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function fetchConfigStatus(): Promise<ConfigStatusResponse> {
  return requestJson<ConfigStatusResponse>("/api/config/status");
}

export async function searchPapers(input: {
  query: string;
  limit: number;
  source: SearchSource;
  verbose: boolean;
}): Promise<SearchResponse> {
  return requestJson<SearchResponse>("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
}

export async function submitAnalyze(input: {
  file: File;
  rounds: number;
  forceReconvert: boolean;
  verbose: boolean;
}): Promise<AnalyzeSubmitResponse> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append("rounds", String(input.rounds));
  formData.append("force_reconvert", String(input.forceReconvert));
  formData.append("verbose", String(input.verbose));
  return requestJson<AnalyzeSubmitResponse>("/api/analyze", {
    method: "POST",
    body: formData
  });
}

export async function fetchJob(jobId: string): Promise<AnalyzeJobStatusResponse> {
  return requestJson<AnalyzeJobStatusResponse>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export async function fetchWorkflowJob<T = unknown>(jobId: string): Promise<WorkflowJobStatusResponse<T>> {
  return requestJson<WorkflowJobStatusResponse<T>>(`/api/workflow-jobs/${encodeURIComponent(jobId)}`);
}

export async function submitConvertUpload(input: {
  file: File;
  outputPath: string;
  force: boolean;
}): Promise<WorkflowSubmitResponse> {
  const formData = new FormData();
  formData.append("file", input.file);
  if (input.outputPath.trim()) {
    formData.append("output_path", input.outputPath.trim());
  }
  formData.append("force", String(input.force));
  return requestJson<WorkflowSubmitResponse>("/api/convert/upload", {
    method: "POST",
    body: formData
  });
}

export async function submitConvertPath(input: {
  pdfPath: string;
  folderPath: string;
  outputPath: string;
  force: boolean;
}): Promise<WorkflowSubmitResponse> {
  return requestJson<WorkflowSubmitResponse>("/api/convert/path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pdf_path: input.pdfPath.trim() || null,
      folder_path: input.folderPath.trim() || null,
      output_path: input.outputPath.trim() || null,
      force: input.force
    })
  });
}

export async function submitDebate(input: {
  paper: string;
  outputPath: string;
  saveReport: boolean;
  rounds: number;
  force: boolean;
  verbose: boolean;
}): Promise<WorkflowSubmitResponse> {
  return requestJson<WorkflowSubmitResponse>("/api/debate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paper: input.paper,
      output_path: input.outputPath.trim() || null,
      save_report: input.saveReport,
      rounds: input.rounds,
      force: input.force,
      verbose: input.verbose
    })
  });
}

export async function submitCourt(input: {
  paperId: string;
  outputPath: string;
  rounds: number;
  verbose: boolean;
}): Promise<WorkflowSubmitResponse> {
  return requestJson<WorkflowSubmitResponse>("/api/court", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paper_id: input.paperId,
      output_path: input.outputPath.trim() || null,
      rounds: input.rounds,
      verbose: input.verbose
    })
  });
}

export async function fetchRAGStatus(): Promise<RAGStatusResult> {
  return requestJson<RAGStatusResult>("/api/rag/status");
}

export async function submitRAGIndex(input: { paperId: string; dryRun: boolean }): Promise<WorkflowSubmitResponse> {
  return requestJson<WorkflowSubmitResponse>("/api/rag/index", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper_id: input.paperId, dry_run: input.dryRun })
  });
}

export async function submitRAGDelete(input: { paperId: string }): Promise<WorkflowSubmitResponse> {
  return requestJson<WorkflowSubmitResponse>("/api/rag/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper_id: input.paperId })
  });
}

export async function searchRAG(input: {
  content: string;
  paperId: string;
  topK: number;
  sectionType: string;
  scoreThreshold: string;
  contextMaxChars: number;
}): Promise<RAGSearchResult> {
  const score = input.scoreThreshold.trim();
  return requestJson<RAGSearchResult>("/api/rag/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content: input.content,
      paper_id: input.paperId.trim() || null,
      top_k: input.topK,
      section_type: input.sectionType.trim() || null,
      score_threshold: score ? Number(score) : null,
      context_max_chars: input.contextMaxChars
    })
  });
}

export async function createChatSession(): Promise<ChatSessionResponse> {
  return requestJson<ChatSessionResponse>("/api/chat/sessions", { method: "POST" });
}

export async function sendChatTurn(sessionId: string, message: string): Promise<ChatTurnResponse> {
  return requestJson<ChatTurnResponse>(`/api/chat/sessions/${encodeURIComponent(sessionId)}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
}

export async function fetchPapers(query: string, limit = 50): Promise<PaperListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (query.trim()) {
    params.set("query", query.trim());
  }
  return requestJson<PaperListResponse>(`/api/papers?${params.toString()}`);
}

export async function fetchPaperDetail(paperId: string): Promise<PaperDetailResponse> {
  return requestJson<PaperDetailResponse>(`/api/papers/${encodeURIComponent(paperId)}`);
}
