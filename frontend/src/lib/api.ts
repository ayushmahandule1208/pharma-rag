// For GitHub Pages static deployment, use full backend URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL 
  ? `${process.env.NEXT_PUBLIC_API_URL}/api`
  : "/api";

export interface Source {
  drug: string;
  section: string;
  score: number;
  is_priority: boolean;
  bm25_score?: number;
  vector_score?: number;
  rerank_score?: number;
  text?: string;
  page_start?: number;
  page_end?: number;
}

export interface Timing {
  retrieve_ms?: number;
  generate_ms?: number;
  total_ms: number;
}

export interface GuardResult {
  passed: boolean;
  category: string;
  confidence: number;
}

export interface QueryResponse {
  answer: string;
  query_type: string;
  sources: Source[];
  timing?: Timing;
  guard_result?: GuardResult;
}

export interface DocumentFamily {
  family_id: string;
  drug_name: string;
  authority: string;
  doc_type: string;
  version_count: number;
  latest_date: string;
}

export interface DocumentVersion {
  doc_id: string;
  version_num: number;
  version_date: string;
  is_latest: number;
  supersedes: string | null;
}

export interface SystemMetrics {
  families: number;
  documents: number;
  search_units: number;
  queries_logged: number;
  vectors?: number;
  avg_response_time?: number;
  avg_score?: number;
}

export interface SearchStats {
  total_documents: number;
  bm25_indexed: number;
  vector_indexed: number;
  reranker_enabled: boolean;
  embedding_model: string;
  reranker_model?: string;
}

// Query the RAG system
export async function queryRAG(question: string, options?: {
  top_k?: number;
  use_hybrid?: boolean;
  use_reranker?: boolean;
  use_guard?: boolean;
}): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      question,
      top_k: options?.top_k ?? 5,
      use_hybrid: options?.use_hybrid ?? true,
      use_reranker: options?.use_reranker ?? true,
      use_guard: options?.use_guard ?? true,
    }),
  });
  if (!res.ok) throw new Error("Query failed");
  return res.json();
}

// Get document families
export async function getDocuments(): Promise<DocumentFamily[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

// Get versions for a family
export async function getVersions(familyId: string): Promise<DocumentVersion[]> {
  const res = await fetch(`${API_BASE}/documents/${familyId}/versions`);
  if (!res.ok) throw new Error("Failed to fetch versions");
  return res.json();
}

// Get system metrics
export async function getMetrics(): Promise<SystemMetrics> {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

// Get search engine stats
export async function getSearchStats(): Promise<SearchStats> {
  const res = await fetch(`${API_BASE}/search/stats`);
  if (!res.ok) throw new Error("Failed to fetch search stats");
  return res.json();
}

// Rebuild search index
export async function rebuildSearchIndex(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/search/rebuild`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to rebuild index");
  return res.json();
}
