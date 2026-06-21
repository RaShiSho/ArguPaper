import type {
  AnalyzeJobStatusResponse,
  AnalyzeSubmitResponse,
  ConfigStatusResponse,
  PaperDetailResponse,
  PaperListResponse,
  SearchResponse,
  SearchSource
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
