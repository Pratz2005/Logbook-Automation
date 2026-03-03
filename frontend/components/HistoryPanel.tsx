"use client";

import { useState } from "react";
import { HistoryEntry } from "@/lib/api";

interface Props {
  entries: HistoryEntry[];
  loading: boolean;
}

export default function HistoryPanel({ entries, loading }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="space-y-2.5">
        {[1, 2, 3].map(i => (
          <div key={i} className="section-card h-14 animate-pulse" style={{ opacity: 0.5 }} />
        ))}
      </div>
    );
  }

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
          key={entry.id}
          className="section-card overflow-hidden animate-fade-up"
          style={{ animationDelay: `${i * 40}ms` }}
        >
          <button
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--paper-warm)] transition-colors"
            onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
          >
            <div className="flex items-center gap-3">
              <span
                className="w-7 h-7 rounded flex items-center justify-center flex-shrink-0"
                style={{ background: "var(--ink)", color: "var(--paper)" }}
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <rect x="2" y="1" width="8" height="11" rx="1" stroke="currentColor" strokeWidth="1.2"/>
                  <path d="M4 4h5M4 6.5h5M4 9h3" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/>
                </svg>
              </span>
              <div className="text-left">
                <p className="text-[12.5px] font-medium text-[var(--ink)]">{entry.entry_name}</p>
                <p className="font-mono text-[10.5px] text-[var(--ink-muted)]">
                  {entry.period_start} – {entry.period_end}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-[10px] text-[var(--ink-muted)]">
                {new Date(entry.created_at).toLocaleDateString("en-SG", { day: "numeric", month: "short" })}
              </span>
              <svg
                width="11" height="11" viewBox="0 0 11 11" fill="none"
                style={{
                  transform: expanded === entry.id ? "rotate(90deg)" : "rotate(0)",
                  transition: "transform 0.2s",
                  color: "var(--ink-muted)",
                }}
              >
                <path d="M3.5 2L7.5 5.5L3.5 9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          </button>

          {expanded === entry.id && (
            <div className="px-4 pb-4 border-t animate-fade-up" style={{ borderColor: "var(--border)" }}>
              <div className="mt-3 space-y-3">
                <div>
                  <p className="section-letter mb-1.5">Section A Preview</p>
                  <p className="text-[12px] text-[var(--ink)] leading-relaxed line-clamp-4">{entry.section_a}</p>
                </div>
                {/* {entry.token_usage && (
                  <p className="font-mono text-[10px] text-[var(--ink-muted)]">
                    {entry.token_usage.total_tokens} tokens · ≈${entry.token_usage.estimated_cost_usd.toFixed(4)}
                  </p>
                )} */}
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
                    Download .docx
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
