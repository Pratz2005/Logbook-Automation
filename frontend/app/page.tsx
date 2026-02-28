"use client";

import { useEffect, useRef, useState } from "react";
import MetadataPanel from "@/components/MetadataPanel";
import NotesPanel from "@/components/NotesPanel";
import PreviewPanel from "@/components/PreviewPanel";
import HistoryPanel from "@/components/HistoryPanel";
import {
  StudentMetadata,
  GenerateResponse,
  generateLogbook,
  loadMetadata,
  loadObjective,
  saveObjective,
  saveMetadata,
  saveLocalHistory,
} from "@/lib/api";

type Tab = "input" | "preview" | "history";

export default function Home() {
  // ── State ──────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<Tab>("input");

  const [metadata, setMetadata] = useState<Partial<StudentMetadata>>({
    student_name: "", matric_number: "", company: "",
    supervisor: "", entry_number: 1,
    period_start: "", period_end: "", submission_date: "",
  });

  const [objective, setObjective] = useState("");
  const [rawNotes, setRawNotes] = useState("");
  const [challenges, setChallenges] = useState("");
  const [achievements, setAchievements] = useState("");
  const [priorSectionA, setPriorSectionA] = useState("");
  const [priorSectionC, setPriorSectionC] = useState("");

  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputRef = useRef<HTMLDivElement>(null);

  // ── Load persisted data ─────────────────────────────────────────
  useEffect(() => {
    const saved = loadMetadata();
    if (Object.keys(saved).length > 0) {
      setMetadata(prev => ({ ...prev, ...saved }));
    }
    const obj = loadObjective();
    if (obj) setObjective(obj);
  }, []);

  // Auto-save objective
  useEffect(() => {
    if (objective) saveObjective(objective);
  }, [objective]);

  // ── Generate ────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setError(null);

    // Client-side validation
    const requiredMeta: (keyof StudentMetadata)[] = [
      "student_name", "matric_number", "company", "supervisor",
      "entry_number", "period_start", "period_end", "submission_date"
    ];
    const missing = requiredMeta.filter(k => !metadata[k]?.toString().trim());
    if (missing.length > 0) {
      setError(`Please fill in: ${missing.join(", ")}`);
      return;
    }
    if (!rawNotes.trim()) {
      setError("Daily work notes cannot be empty.");
      return;
    }
    if (!objective.trim()) {
      setError("Internship objective is required.");
      return;
    }

    setIsLoading(true);
    setActiveTab("preview");

    try {
      const response = await generateLogbook({
        metadata: metadata as StudentMetadata,
        raw_notes: rawNotes,
        internship_objective: objective,
        challenges,
        achievements,
        prior_section_a: priorSectionA,
        prior_section_c: priorSectionC,
      });

      setResult(response);

      // Save to local history
      saveLocalHistory({
        entry_number: Number(metadata.entry_number),
        period_start: String(metadata.period_start),
        period_end: String(metadata.period_end),
        generated_at: new Date().toISOString(),
        section_a: response.section_a,
        section_c: response.section_c,
        presigned_url: response.s3_info?.presigned_url,
        s3_key: response.s3_info?.s3_key,
      });

      // Update prior entries for next generation
      setPriorSectionA(response.section_a);
      setPriorSectionC(response.section_c);

      // Bump entry number
      setMetadata(prev => ({
        ...prev,
        entry_number: (Number(prev.entry_number) || 1) + 1,
      }));

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
      setActiveTab("input");
    } finally {
      setIsLoading(false);
    }
  };

  const canGenerate = !isLoading && !!rawNotes.trim() && !!objective.trim();

  // ── Render ──────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", background: "var(--paper-cool)" }}>
      {/* ── Top bar ── */}
      <header
        style={{
          background: "var(--ink)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <div
          style={{
            maxWidth: 1440,
            margin: "0 auto",
            padding: "0 24px",
            height: 52,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div
              className="flex items-center justify-center w-7 h-7 rounded"
              style={{ background: "var(--accent)", flexShrink: 0 }}
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <rect x="2" y="1" width="11" height="13" rx="1.5" stroke="white" strokeWidth="1.2"/>
                <path d="M5 5h5M5 7.5h5M5 10h3" stroke="white" strokeWidth="1.1" strokeLinecap="round"/>
              </svg>
            </div>
            <div>
              <span
                className="font-display font-semibold text-[var(--paper)] text-[13.5px]"
                style={{ letterSpacing: "0.01em" }}
              >
                NTU Logbook
              </span>
              <span
                className="ml-2 text-[10.5px] font-light"
                style={{ color: "rgba(245,240,232,0.45)", letterSpacing: "0.04em" }}
              >
                Generator
              </span>
            </div>
          </div>

          {/* Nav pills */}
          <div
            className="flex items-center gap-1 p-1 rounded-[20px]"
            style={{ background: "rgba(255,255,255,0.07)" }}
          >
            {(["input", "preview", "history"] as Tab[]).map(tab => (
              <button
                key={tab}
                className="nav-pill capitalize"
                style={
                  activeTab === tab
                    ? { background: "var(--paper)", color: "var(--ink)", fontWeight: 500 }
                    : { color: "rgba(245,240,232,0.55)" }
                }
                onClick={() => setActiveTab(tab)}
              >
                {tab === "preview" && isLoading ? (
                  <span className="flex items-center gap-1.5">
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full border border-[var(--accent)] border-t-transparent"
                      style={{ animation: "spin-slow 0.8s linear infinite" }}
                    />
                    Preview
                  </span>
                ) : tab}
              </button>
            ))}
          </div>

          {/* Generate button */}
          <button
            className="btn-accent flex items-center gap-2 text-[12.5px]"
            style={{ padding: "7px 18px" }}
            onClick={handleGenerate}
            disabled={!canGenerate}
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M6.5 1.5L8.5 5.5H12L9 8l1 4-3.5-2.5L3 12l1-4L1 5.5h3.5z" stroke="white" strokeWidth="1.2" strokeLinejoin="round" fill="none"/>
            </svg>
            {isLoading ? "Generating…" : "Generate"}
          </button>
        </div>
      </header>

      {/* ── Main layout ── */}
      <div
        style={{
          maxWidth: 1440,
          margin: "0 auto",
          padding: "24px 24px",
          display: "grid",
          gridTemplateColumns: activeTab !== "history" ? "360px 1fr" : "1fr",
          gap: 20,
          minHeight: "calc(100vh - 52px)",
        }}
      >
        {/* LEFT: Input panel (hidden on mobile preview/history) */}
        {(activeTab === "input" || activeTab === "preview") && (
          <div
            ref={inputRef}
            className="section-card p-5 animate-fade-up h-fit"
            style={{ position: "sticky", top: 72, maxHeight: "calc(100vh - 90px)", overflowY: "auto" }}
          >
            {/* Error banner */}
            {error && (
              <div
                className="mb-4 px-3 py-2.5 rounded-[4px] flex gap-2 animate-fade-up"
                style={{ background: "var(--error-light)", border: "1px solid rgba(155,35,53,0.2)" }}
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
                  <circle cx="6.5" cy="6.5" r="5.5" stroke="var(--error)" strokeWidth="1.1"/>
                  <path d="M6.5 4v3" stroke="var(--error)" strokeWidth="1.2" strokeLinecap="round"/>
                  <circle cx="6.5" cy="8.5" r="0.6" fill="var(--error)"/>
                </svg>
                <p className="text-[12px] text-[var(--error)]">{error}</p>
              </div>
            )}

            {/* Metadata */}
            <MetadataPanel value={metadata} onChange={setMetadata} />

            <hr className="rule-line mt-5" />

            {/* Notes */}
            <div className="mt-5">
              <NotesPanel
                rawNotes={rawNotes}
                objective={objective}
                challenges={challenges}
                achievements={achievements}
                priorSectionA={priorSectionA}
                priorSectionC={priorSectionC}
                onRawNotesChange={setRawNotes}
                onObjectiveChange={setObjective}
                onChallengesChange={setChallenges}
                onAchievementsChange={setAchievements}
                onPriorAChange={setPriorSectionA}
                onPriorCChange={setPriorSectionC}
              />
            </div>

            {/* Mobile generate */}
            <div className="mt-5">
              <button
                className="btn-primary w-full flex items-center justify-center gap-2"
                onClick={handleGenerate}
                disabled={!canGenerate}
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M6.5 1.5L8.5 5.5H12L9 8l1 4-3.5-2.5L3 12l1-4L1 5.5h3.5z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" fill="none"/>
                </svg>
                {isLoading ? "Generating logbook…" : "Generate Logbook"}
              </button>
            </div>
          </div>
        )}

        {/* RIGHT: Preview / History panel */}
        <div className="min-w-0">
          {activeTab === "history" ? (
            <div className="section-card p-5 animate-fade-up">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <p className="section-letter mb-0.5">Past Submissions</p>
                  <h2 className="font-display text-lg font-semibold text-[var(--ink)]" style={{ lineHeight: 1.2 }}>
                    History
                  </h2>
                </div>
              </div>
              <HistoryPanel />
            </div>
          ) : (
            <div className="section-card p-5 animate-fade-up" style={{ minHeight: 400 }}>
              <div className="flex items-center justify-between mb-5">
                <div>
                  <p className="section-letter mb-0.5">Live Preview</p>
                  <h2 className="font-display text-lg font-semibold text-[var(--ink)]" style={{ lineHeight: 1.2 }}>
                    Generated Logbook
                  </h2>
                </div>
                {result && (
                  <span className="tag tag-success flex items-center gap-1.5">
                    <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
                      <circle cx="4.5" cy="4.5" r="4" fill="var(--success)"/>
                      <path d="M2.5 4.5l1.5 1.5 2.5-2.5" stroke="white" strokeWidth="1" strokeLinecap="round"/>
                    </svg>
                    Ready
                  </span>
                )}
              </div>
              <PreviewPanel
                result={result}
                isLoading={isLoading}
                studentName={String(metadata.student_name || "")}
                entryNumber={Number(metadata.entry_number) || 1}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Footer ── */}
      <footer
        className="text-center py-5"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <p className="font-mono text-[10.5px] text-[var(--ink-muted)]">
          NTU Logbook Generator · claude-sonnet-4-6 ·{" "}
          <span style={{ color: "var(--accent)" }}>python-docx + FastAPI + Next.js</span>
        </p>
      </footer>
    </div>
  );
}
