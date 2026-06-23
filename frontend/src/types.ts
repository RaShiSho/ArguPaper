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

export interface WorkflowSubmitResponse {
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

export interface WorkflowJobStatusResponse<T = unknown> {
  job_id: string;
  kind: string;
  label: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  progress: JobProgressMessage[];
  warnings: string[];
  result?: T | null;
  error?: string | null;
}

export interface ConvertWorkflowResult {
  conversion?: {
    cache_key: string;
    from_cache: boolean;
    markdown?: string | null;
  } | null;
  summary?: {
    total_entries: number;
    processed: number;
    success: number;
    cache_hits: number;
    failed: number;
    skipped: number;
  } | null;
  input_path?: string | null;
  cache_path?: string | null;
  output_path?: string | null;
  run_log_path?: string | null;
}

export interface CourtWorkflowResult {
  paper_id: string;
  report_title: string;
  report_markdown: string;
  saved_report_path?: string | null;
  warnings: string[];
}

export interface RAGStatusResult {
  rag_enabled: boolean;
  ollama_base_url: string;
  ollama_embed_model: string;
  milvus_uri: string;
  milvus_collection: string;
  top_k: number;
  chunk_size: number;
  chunk_overlap: number;
  include_references: boolean;
  vector_dim: number;
  run_log_path?: string | null;
}

export interface RAGChunk {
  chunk_id: string;
  paper_id: string;
  section?: string | null;
  section_type?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  score: number;
  text: string;
}

export interface RAGSearchResult {
  content: string;
  paper_id?: string | null;
  top_k: number;
  chunks: RAGChunk[];
  context: string;
  warnings: string[];
  run_log_path?: string | null;
}

export interface RAGIndexResult {
  paper_id: string;
  chunk_count: number;
  embedding_dim?: number | null;
  skipped_sections: string[];
  warnings: string[];
  dry_run: boolean;
  run_log_path?: string | null;
}

export interface RAGDeleteResult {
  paper_id: string;
  deleted_count?: number | null;
  warnings: string[];
  run_log_path?: string | null;
}

export interface ChatSessionResponse {
  session_id: string;
}

export interface ChatTurnResponse {
  response: string;
  interrupted: boolean;
  warnings: string[];
  selected_paper?: {
    paper_id: string;
    title: string;
    source: string;
    library_status: string;
  } | null;
  log_path?: string | null;
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
  library_status?: "converted" | "analyzed";
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
  log_path: string;
  search_log_path: string;
  convert_log_path: string;
  web_log_path: string;
  analyze_retrieval_loop_enabled: boolean;
}
