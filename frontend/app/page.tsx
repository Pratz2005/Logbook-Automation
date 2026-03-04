"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import MetadataPanel from "@/components/MetadataPanel";
import NotesPanel from "@/components/NotesPanel";
import PreviewPanel from "@/components/PreviewPanel";
import HistoryPanel from "@/components/HistoryPanel";
import LoginPanel from "@/components/LoginPanel";
import {
  StudentMetadata,
  GenerateResponse,
  HistoryEntry,
  UserProfile,
  generateLogbook,
  fetchProfile,
  fetchHistory,
  updateProfile,
} from "@/lib/api";
import { supabase } from "@/lib/supabase";

type Tab = "input" | "preview" | "history";

export default function Home() {
  // ── Auth state ──────────────────────────────────────────────────
  const [authReady, setAuthReady] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  // ── Form state ──────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<Tab>("input");

  const [metadata, setMetadata] = useState<Partial<StudentMetadata>>({
    student_name: "", matric_number: "", company: "",
    supervisor: "", entry_name: "",
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

  // ── History state ───────────────────────────────────────────────
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const inputRef = useRef<HTMLDivElement>(null);
  const objectiveSaveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Load session and profile on mount ───────────────────────────
  useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      if (data.session) {
        try {
          const p = await fetchProfile();
          applyProfile(p);
        } catch {
          // Session expired or invalid — sign out cleanly
          await supabase.auth.signOut();
        }
      }
      setAuthReady(true);
    });

    // Listen for auth changes (e.g. session expiry)
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_OUT") {
        setProfile(null);
        setHistory([]);
      }
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  const applyProfile = (p: UserProfile) => {
    setProfile(p);
    setMetadata(prev => ({
      ...prev,
      student_name: p.student_name,
      matric_number: p.matric_number,
      company: p.company,
      supervisor: p.supervisor,
    }));
    setObjective(p.internship_objective || "");
  };

  // ── Fetch history when logged in ─────────────────────────────────
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const { entries } = await fetchHistory();
      setHistory(entries);
    } catch {
      // Non-fatal
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (profile) loadHistory();
  }, [profile, loadHistory]);

  // ── Auto-save objective (debounced) ──────────────────────────────
  useEffect(() => {
    if (!profile || !objective) return;
    if (objectiveSaveTimeout.current) clearTimeout(objectiveSaveTimeout.current);
    objectiveSaveTimeout.current = setTimeout(() => {
      updateProfile({ internship_objective: objective }).catch(() => {});
    }, 1500);
    return () => {
      if (objectiveSaveTimeout.current) clearTimeout(objectiveSaveTimeout.current);
    };
  }, [objective, profile]);

  // ── Login callback ────────────────────────────────────────────────
  const handleLogin = (p: UserProfile) => {
    applyProfile(p);
    setAuthReady(true);
  };

  // ── Logout ────────────────────────────────────────────────────────
  const handleLogout = async () => {
    await supabase.auth.signOut();
    setProfile(null);
    setHistory([]);
    setResult(null);
    setObjective("");
    setRawNotes("");
    setPriorSectionA("");
    setPriorSectionC("");
    setMetadata({
      student_name: "", matric_number: "", company: "",
      supervisor: "", entry_name: "",
      period_start: "", period_end: "", submission_date: "",
    });
  };

  // ── Generate ──────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setError(null);

    const requiredMeta: (keyof StudentMetadata)[] = [
      "student_name", "matric_number", "company", "supervisor",
      "entry_name", "period_start", "period_end", "submission_date"
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

      // Update prior entries for next generation (style continuity)
      setPriorSectionA(response.section_a);
      setPriorSectionC(response.section_c);

      // Refresh history from DB
      await loadHistory();

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
      setActiveTab("input");
    } finally {
      setIsLoading(false);
    }
  };

  const canGenerate = !isLoading && !!rawNotes.trim() && !!objective.trim();

  // ── Not ready yet ─────────────────────────────────────────────────
  if (!authReady) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--paper-cool)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div
          className="w-8 h-8 rounded-full border-2 border-[var(--accent)] border-t-transparent"
          style={{ animation: "spin-slow 0.8s linear infinite" }}
        />
      </div>
    );
  }

  // ── Not logged in ─────────────────────────────────────────────────
  if (!profile) {
    return <LoginPanel onLogin={handleLogin} />;
  }

  // ── Main UI ───────────────────────────────────────────────────────
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
          className="header-inner"
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
              <span className="font-display font-semibold text-[var(--paper)] text-[13.5px]" style={{ letterSpacing: "0.01em" }}>
                NTU Logbook
              </span>
              <span className="ml-2 text-[10.5px] font-light hidden sm:inline" style={{ color: "rgba(245,240,232,0.45)", letterSpacing: "0.04em" }}>
                Generator
              </span>
            </div>
          </div>

          {/* Nav pills */}
          <div className="flex items-center gap-1 p-1 rounded-[20px]" style={{ background: "rgba(255,255,255,0.07)" }}>
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

          {/* Right side: user info + generate */}
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-[11px] font-medium text-[var(--paper)]">{profile.student_name}</p>
              <p className="text-[10px]" style={{ color: "rgba(245,240,232,0.45)" }}>{profile.matric_number}</p>
            </div>
            <button
              onClick={handleLogout}
              className="btn-secondary text-[11.5px] flex items-center gap-1.5"
              style={{ color: "rgba(245,240,232,0.55)", background: "rgba(255,255,255,0.07)", border: "none" }}
              title="Sign out"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M8 4l3 2.5-3 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                <path d="M11 6.5H5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                <path d="M5 2H2a1 1 0 00-1 1v6a1 1 0 001 1h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
              </svg>
            </button>
            <button
              className="btn-accent flex items-center gap-2 text-[12.5px] hidden md:flex"
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
        </div>
      </header>

      {/* ── Main layout ── */}
      <div
        className="main-layout-grid"
        style={{
          maxWidth: 1440,
          margin: "0 auto",
          padding: "24px",
          display: "grid",
          gridTemplateColumns: activeTab !== "history" ? "360px 1fr" : "1fr",
          gap: 20,
          minHeight: "calc(100vh - 52px)",
        }}
      >
        {/* LEFT: Input panel — on mobile only visible in "input" tab */}
        {(activeTab === "input" || activeTab === "preview") && (
          <div
            ref={inputRef}
            className={`section-card p-5 animate-fade-up h-fit panel-input-sticky${activeTab === "preview" ? " hidden md:block" : ""}`}
          >
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

            <MetadataPanel value={metadata} onChange={setMetadata} profile={profile} />

            <hr className="rule-line mt-5" />

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

            <div className="mt-5 hidden md:block">
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

        {/* RIGHT: Preview / History — on mobile only visible in "preview"/"history" tabs */}
        <div className={`min-w-0${activeTab === "input" ? " hidden md:block" : ""}`}>
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
              <HistoryPanel entries={history} loading={historyLoading} />
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
                entryName={String(metadata.entry_name || "")}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Mobile sticky generate bar ── */}
      {activeTab === "input" && (
        <div
          className="md:hidden fixed bottom-0 left-0 right-0 px-3 py-3"
          style={{
            background: "var(--paper-cool)",
            borderTop: "1px solid var(--border)",
            zIndex: 40,
            boxShadow: "0 -4px 16px rgba(15,25,35,0.07)",
          }}
        >
          <button
            className="btn-accent w-full flex items-center justify-center gap-2"
            style={{ padding: "12px 22px", fontSize: "13.5px" }}
            onClick={handleGenerate}
            disabled={!canGenerate}
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M6.5 1.5L8.5 5.5H12L9 8l1 4-3.5-2.5L3 12l1-4L1 5.5h3.5z" stroke="white" strokeWidth="1.2" strokeLinejoin="round" fill="none"/>
            </svg>
            {isLoading ? "Generating logbook…" : "Generate Logbook"}
          </button>
        </div>
      )}

      {/* ── Footer ── */}
      <footer className="text-center py-5" style={{ borderTop: "1px solid var(--border)" }}>
        <p className="font-mono text-[10.5px] text-[var(--ink-muted)]">
          NTU Logbook Generator{" "}
        </p>
      </footer>
    </div>
  );
}
