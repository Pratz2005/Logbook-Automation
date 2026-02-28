/**
 * API client for the NTU Logbook Generator FastAPI backend.
 * Includes debouncing (min 2s between calls) and request timeout.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StudentMetadata {
  student_name: string;
  matric_number: string;
  company: string;
  supervisor: string;
  entry_number: number;
  period_start: string;  // DD/MM/YYYY
  period_end: string;    // DD/MM/YYYY
  submission_date: string; // DD/MM/YYYY
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
  s3_info: {
    presigned_url?: string;
    s3_key?: string;
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
  s3_key: string;
  last_modified: string;
  file_size_bytes: number;
  presigned_url: string;
}

// Debounce tracking
let lastCallTime = 0;
const MIN_INTERVAL_MS = 2000;

async function apiCall<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 120_000
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
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

export async function generateLogbook(req: GenerateRequest): Promise<GenerateResponse> {
  // Enforce minimum 2s debounce
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

export async function getHistory(studentName: string): Promise<{ entries: HistoryEntry[]; count: number }> {
  if (!studentName.trim()) return { entries: [], count: 0 };
  const encoded = encodeURIComponent(studentName);
  return apiCall(`/api/history/${encoded}`);
}

/**
 * Download docx from base64 string (returned inline in generate response)
 */
export function downloadDocxFromBase64(base64: string, filename: string): void {
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  const blob = new Blob([bytes], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ── localStorage helpers ─────────────────────────────────────────

const METADATA_KEY = "ntu_logbook_metadata";
const OBJECTIVE_KEY = "ntu_logbook_objective";
const HISTORY_KEY = "ntu_logbook_history";

export function saveMetadata(metadata: StudentMetadata): void {
  try {
    localStorage.setItem(METADATA_KEY, JSON.stringify(metadata));
  } catch {}
}

export function loadMetadata(): Partial<StudentMetadata> {
  try {
    const raw = localStorage.getItem(METADATA_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveObjective(objective: string): void {
  try {
    localStorage.setItem(OBJECTIVE_KEY, objective);
  } catch {}
}

export function loadObjective(): string {
  try {
    return localStorage.getItem(OBJECTIVE_KEY) || "";
  } catch {
    return "";
  }
}

export interface LocalHistoryEntry {
  entry_number: number;
  period_start: string;
  period_end: string;
  generated_at: string;
  section_a: string;
  section_c: string;
  presigned_url?: string;
  s3_key?: string;
}

export function saveLocalHistory(entry: LocalHistoryEntry): void {
  try {
    const existing = loadLocalHistory();
    const updated = [entry, ...existing.filter((e) => e.entry_number !== entry.entry_number)].slice(0, 20);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  } catch {}
}

export function loadLocalHistory(): LocalHistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
