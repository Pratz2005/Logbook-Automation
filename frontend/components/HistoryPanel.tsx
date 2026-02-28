"use client";

import { LocalHistoryEntry, loadLocalHistory, downloadDocxFromBase64 } from "@/lib/api";
import { useEffect, useState } from "react";

export default function HistoryPanel() {
  const [entries, setEntries] = useState<LocalHistoryEntry[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    setEntries(loadLocalHistory());
  }, []);

  if (entries.length === 0) {
    return (
      <div className="text-center py-10 animate-fade-up">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4"
          style={{ background: "var(--paper-warm)", border: "1px solid var(--border)" }}
        >
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <circle cx="11" cy="11" r="9" stroke="var(--ink-muted)" strokeWidth="1.3"/>
            <path d="M11 6v5l3 2" stroke="var(--ink-muted)" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
        </div>
        <p className="text-[13px] font-medium text-[var(--ink)]">No history yet</p>
        <p className="text-[11.5px] text-[var(--ink-muted)] mt-1">Generated entries will appear here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5 animate-fade-up">
      <div className="flex items-center justify-between mb-4">
        <p className="section-letter">Past Entries</p>
        <span className="tag tag-neutral">{entries.length} entries</span>
      </div>

      {entries.map((entry, i) => (
        <div
          key={entry.entry_number}
          className="section-card overflow-hidden animate-fade-up"
          style={{ animationDelay: `${i * 40}ms` }}
        >
          {/* Header row */}
          <button
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--paper-warm)] transition-colors"
            onClick={() => setExpanded(expanded === entry.entry_number ? null : entry.entry_number)}
          >
            <div className="flex items-center gap-3">
              <span
                className="w-7 h-7 rounded flex items-center justify-center text-[11px] font-bold font-display"
                style={{ background: "var(--ink)", color: "var(--paper)" }}
              >
                {entry.entry_number}
              </span>
              <div className="text-left">
                <p className="text-[12.5px] font-medium text-[var(--ink)]">
                  Entry {entry.entry_number}
                </p>
                <p className="font-mono text-[10.5px] text-[var(--ink-muted)]">
                  {entry.period_start} – {entry.period_end}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-[10px] text-[var(--ink-muted)]">
                {new Date(entry.generated_at).toLocaleDateString("en-SG", { day: "numeric", month: "short" })}
              </span>
              <svg
                width="11" height="11" viewBox="0 0 11 11" fill="none"
                style={{
                  transform: expanded === entry.entry_number ? "rotate(90deg)" : "rotate(0)",
                  transition: "transform 0.2s",
                  color: "var(--ink-muted)"
                }}
              >
                <path d="M3.5 2L7.5 5.5L3.5 9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          </button>

          {/* Expanded content */}
          {expanded === entry.entry_number && (
            <div
              className="px-4 pb-4 border-t animate-fade-up"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="mt-3 space-y-3">
                <div>
                  <p className="section-letter mb-1.5">Section A Preview</p>
                  <p className="text-[12px] text-[var(--ink)] leading-relaxed line-clamp-4">
                    {entry.section_a}
                  </p>
                </div>
                {entry.presigned_url && (
                  <a
                    href={entry.presigned_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary inline-flex items-center gap-1.5 text-[11.5px]"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <path d="M6 1v6M3.5 5.5L6 8l2.5-2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                      <path d="M1.5 9.5h9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                    </svg>
                    Download from S3
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
