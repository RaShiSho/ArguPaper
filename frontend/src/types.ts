export type SearchSource = "semantic_scholar" | "arxiv" | "google_scholar" | "serpapi" | "both";

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface SearchResult {
  title: string;
  authors: string[];
  year: number | null;
  venue: string;
  citation_count: number;
  url: string;
  source: string;
  abstract?: string | null;
}

export interface SearchParseResult {
  raw_request: string;
  filters: {
    keywords: string[];
    year_from?: number | null;
    year_to?: number | null;
    target_count?: number | null;
    venue_policy?: string | null;
    source_preference?: SearchSource | null;
  };
  parser: string;
  parser_notes: string[];
}

export interface SearchAgentResult {
  results: SearchResult[];
  expanded_queries: string[];
  source_stats: Record<string, number>;
  warnings: string[];
  trace_dir: string;
  parse_result: SearchParseResult;
  retrieved_count: number;
  filtered_count: number;
  candidate_limit: number;
}

export interface SearchResponse {
  result: SearchAgentResult;
}

export interface AnalyzeSubmitResponse {
  job_id: string;
  status: JobStatus;
}

export interface AnalyzeWorkflowResult {
  report_markdown: string;
  report_title: string;
  from_cache: boolean;
  paper_id: string;
  saved_report_path?: string | null;
  supplementary_search_used: boolean;
  warnings: string[];
}

export interface JobProgressMessage {
  message: string;
  timestamp: string;
}

export interface AnalyzeJobStatusResponse {
  job_id: string;
  status: JobStatus;
  upload_filename: string;
  created_at: string;
  updated_at: string;
  progress: JobProgressMessage[];
  warnings: string[];
  result?: AnalyzeWorkflowResult | null;
  error?: string | null;
}

export interface PaperListResponse {
  records: PaperRecord[];
}

export interface PaperRecord {
  paper_id?: string;
  title?: string;
  source?: string;
  updated_at?: string;
  from_cache?: boolean;
}

export interface PaperDetailResponse {
  metadata: Record<string, unknown>;
  abstract: Record<string, unknown>;
  report: string;
  markdown: string;
}

export interface ConfigStatusResponse {
  mineru_api_configured: boolean;
  semantic_scholar_configured: boolean;
  serpapi_configured: boolean;
  paper_storage_path: string;
  cache_path: string;
  search_agent_trace_path: string;
  analyze_retrieval_loop_enabled: boolean;
}
