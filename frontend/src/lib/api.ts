// For GitHub Pages static deployment, use full backend URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL 
  ? `${process.env.NEXT_PUBLIC_API_URL}/api`
  : "/api";

export interface Source {
  drug: string;
  section: string;
  score: number;
  is_priority: boolean;
  text?: string;
  page_start?: number;
  page_end?: number;
}

export interface QueryResponse {
  answer: string;
  query_type: string;
  sources: Source[];
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

// Query the RAG system
export async function queryRAG(question: string): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
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


// ============================================================================
// DRUG COMPARISON API
// ============================================================================

export interface ComparisonResult {
  drug1: string;
  drug2: string;
  indications: {
    drug1: string[];
    drug2: string[];
    shared: string[];
    unique_drug1: string[];
    unique_drug2: string[];
  };
  dosing: {
    drug1: Record<string, string>;
    drug2: Record<string, string>;
  };
  side_effects: {
    drug1: { common: string[]; serious: string[] };
    drug2: { common: string[]; serious: string[] };
    shared: string[];
    unique_drug1: string[];
    unique_drug2: string[];
  };
  warnings: {
    drug1: string[];
    drug2: string[];
  };
  summary: string;
  sources: Record<string, string>;
}

// Get available drugs for comparison
export async function getAvailableDrugs(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/drugs`);
  if (!res.ok) throw new Error("Failed to fetch drugs");
  const data = await res.json();
  return data.drugs;
}

// Compare two drugs
export async function compareDrugs(drug1: string, drug2: string): Promise<ComparisonResult> {
  const res = await fetch(`${API_BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drug1, drug2 }),
  });
  if (!res.ok) throw new Error("Comparison failed");
  return res.json();
}

