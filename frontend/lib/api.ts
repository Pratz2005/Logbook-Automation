/**
 * API client for the NTU Logbook Generator FastAPI backend.
 * Auth: JWT from Supabase session, attached as Authorization: Bearer header.
 */

import { getAccessToken } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StudentMetadata {
  student_name: string;
  matric_number: string;
  company: string;
  supervisor: string;
  entry_name: string;
  period_start: string;   // DD/MM/YYYY
  period_end: string;     // DD/MM/YYYY
  submission_date: string; // DD/MM/YYYY
}

export interface UserProfile {
  id?: string;
  matric_number: string;
  student_name: string;
  company: string;
  supervisor: string;
  internship_objective: string;
}

export interface GenerateRequest {
  metadata: StudentMetadata;
  raw_notes: string;
  internship_objective: string;
  challenges?: string;
  achievements?: string;
  prior_section_a?: string;
  prior_section_c?: string;
}

export interface WorkRow {
  task_description: string;
  date_from: string;
  date_to: string;
  is_leave: boolean;
}

export interface GenerateResponse {
  success: boolean;
  section_a: string;
  section_b_rows: WorkRow[];
  section_c: string;
  storage_info: {
    presigned_url?: string;
    storage_path?: string;
    file_size_bytes?: number;
  };
  summary: string;
  token_usage: {
    total_tokens: number;
    estimated_cost_usd: number;
  };
  warnings: string[];
  docx_base64: string;
}

export interface HistoryEntry {
  id: string;
  entry_name: string;
  period_start: string;
  period_end: string;
  submission_date: string;
  section_a: string;
  section_c: string;
  storage_path: string | null;
  token_usage: { total_tokens: number; estimated_cost_usd: number } | null;
  created_at: string;
  presigned_url: string | null;
}

// ── Debounce tracking ─────────────────────────────────────────────
let lastCallTime = 0;
const MIN_INTERVAL_MS = 2000;

// ── Core fetch wrapper ────────────────────────────────────────────
async function apiCall<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 120_000,
  requireAuth = true,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (requireAuth) {
    const token = await getAccessToken();
    if (!token) throw new Error("Not authenticated. Please sign in.");
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers,
    });

    clearTimeout(timer);

    if (!res.ok) {
      let msg = `API error ${res.status}`;
      try {
        const err = await res.json();
        msg = err.detail || msg;
      } catch {}
      throw new Error(msg);
    }

    return res.json() as Promise<T>;
  } catch (err: unknown) {
    clearTimeout(timer);
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw err;
  }
}

// ── Auth API ──────────────────────────────────────────────────────

export async function registerUser(
  matric_number: string,
  password: string,
  student_name: string,
  company: string,
  supervisor: string,
): Promise<{ access_token: string; refresh_token: string; user_id: string; profile: UserProfile }> {
  return apiCall(
    "/api/auth/register",
    { method: "POST", body: JSON.stringify({ matric_number, password, student_name, company, supervisor }) },
    30_000,
    false,
  );
}

export async function loginUser(
  matric_number: string,
  password: string,
): Promise<{ access_token: string; user_id: string; profile: UserProfile }> {
  return apiCall(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ matric_number, password }) },
    30_000,
    false,
  );
}

// ── Profile API ───────────────────────────────────────────────────

export async function fetchProfile(): Promise<UserProfile> {
  return apiCall<UserProfile>("/api/profile");
}

export async function updateProfile(
  updates: Partial<Pick<UserProfile, "company" | "supervisor" | "internship_objective">>,
): Promise<void> {
  await apiCall("/api/profile", { method: "PUT", body: JSON.stringify(updates) });
}

// ── Generate API ──────────────────────────────────────────────────

export async function generateLogbook(req: GenerateRequest): Promise<GenerateResponse> {
  const now = Date.now();
  const elapsed = now - lastCallTime;
  if (elapsed < MIN_INTERVAL_MS && lastCallTime > 0) {
    const wait = Math.ceil((MIN_INTERVAL_MS - elapsed) / 1000);
    throw new Error(`Please wait ${wait}s before generating again.`);
  }
  lastCallTime = Date.now();

  return apiCall<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// ── History API ───────────────────────────────────────────────────

export async function fetchHistory(): Promise<{ entries: HistoryEntry[]; count: number }> {
  return apiCall<{ entries: HistoryEntry[]; count: number }>("/api/history");
}

// ── DOCX download helpers ─────────────────────────────────────────

const DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

function _triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function downloadDocxFromBase64(base64: string, filename: string): void {
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  _triggerBlobDownload(new Blob([bytes], { type: DOCX_MIME }), filename);
}

/**
 * Fetch a remote DOCX URL (e.g. Supabase signed URL) and trigger a named
 * download. Using fetch+blob instead of <a href target="_blank"> ensures
 * the browser always downloads the file rather than trying to render it,
 * and gives it the correct filename regardless of the URL path.
 */
export async function downloadDocxFromUrl(url: string, filename: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Download failed: ${res.status}`);
  const blob = await res.blob();
  _triggerBlobDownload(
    new Blob([blob], { type: DOCX_MIME }),
    filename,
  );
}
