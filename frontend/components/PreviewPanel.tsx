"use client";

import { GenerateResponse, downloadDocxFromBase64 } from "@/lib/api";

interface Props {
  result: GenerateResponse | null;
  isLoading: boolean;
  studentName?: string;
  entryName?: string;
}

function ShimmerBlock({ rows = 4, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="shimmer h-3 rounded-sm"
          style={{ width: `${65 + Math.random() * 35}%` }}
        />
      ))}
    </div>
  );
}

function SectionBox({
  label,
  letter,
  children,
  delay = 0,
}: {
  label: string;
  letter: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <div
      className="section-card p-4 animate-slide-right"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span
          className="inline-flex items-center justify-center w-6 h-6 rounded text-[11px] font-bold font-display"
          style={{ background: "var(--ink)", color: "var(--paper)" }}
        >
          {letter}
        </span>
        <span className="text-[11px] font-medium tracking-widest uppercase text-[var(--ink-muted)]">
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

export default function PreviewPanel({ result, isLoading, studentName, entryName }: Props) {
  const handleDownload = () => {
    if (!result?.docx_base64) return;
    const name = studentName?.replace(/\s+/g, "_") || "student";
    const entry = entryName?.replace(/\s+/g, "_") || "entry";
    downloadDocxFromBase64(result.docx_base64, `Logbook_${name}_${entry}.docx`);
  };

  // Empty state
  if (!isLoading && !result) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8 animate-fade-up">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
          style={{ background: "var(--paper-warm)", border: "1px solid var(--border)" }}
        >
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="5" y="3" width="18" height="22" rx="2" stroke="var(--ink-muted)" strokeWidth="1.4"/>
            <path d="M9 9h10M9 13h10M9 17h6" stroke="var(--ink-muted)" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
        </div>
        <h3 className="font-display text-base font-semibold text-[var(--ink)] mb-2">
          Preview appears here
        </h3>
        <p className="text-[12.5px] text-[var(--ink-muted)] max-w-[220px] leading-relaxed">
          Fill in your notes and click Generate to see the formatted logbook.
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4 animate-fade-up">
        <div className="flex items-center gap-3 px-1 mb-6">
          <div
            className="w-5 h-5 rounded-full border-2 border-[var(--accent)] border-t-transparent"
            style={{ animation: "spin-slow 0.9s linear infinite" }}
          />
          <div className="space-y-1">
            <p className="text-[12.5px] font-medium text-[var(--ink)]">Generating your logbook…</p>
            <p className="text-[11px] text-[var(--ink-muted)]">Calling Backend(Yes I couldnt think of anything better)</p>
          </div>
        </div>

        <SectionBox label="Objective and Scope" letter="A">
          <ShimmerBlock rows={5} />
        </SectionBox>
        <SectionBox label="Work Done During the Period" letter="B" delay={60}>
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-3">
                <div className="shimmer h-3 rounded-sm" />
                <div className="shimmer h-3 w-16 rounded-sm" />
                <div className="shimmer h-3 w-16 rounded-sm" />
              </div>
            ))}
          </div>
        </SectionBox>
        <SectionBox label="Reflection" letter="C" delay={120}>
          <ShimmerBlock rows={6} />
        </SectionBox>
      </div>
    );
  }

  // Result
  return (
    <div className="space-y-4">
      {/* Warnings */}
      {result!.warnings.length > 0 && (
        <div
          className="px-3 py-2.5 rounded-[4px] flex gap-2.5 animate-fade-up"
          style={{ background: "var(--warning-light)", border: "1px solid rgba(139,105,20,0.2)" }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
            <path d="M7 1.5L12.5 11H1.5L7 1.5z" stroke="var(--warning)" strokeWidth="1.2" strokeLinejoin="round"/>
            <path d="M7 6v2.5" stroke="var(--warning)" strokeWidth="1.2" strokeLinecap="round"/>
            <circle cx="7" cy="9.5" r="0.6" fill="var(--warning)"/>
          </svg>
          <div className="space-y-0.5">
            {result!.warnings.map((w, i) => (
              <p key={i} className="text-[11.5px] text-[var(--warning)]">{w}</p>
            ))}
          </div>
        </div>
      )}

      {/* Section A */}
      <SectionBox label="Objective and Scope of Work" letter="A">
        <p className="text-[13px] text-[var(--ink)] leading-relaxed whitespace-pre-wrap">
          {result!.section_a}
        </p>
      </SectionBox>

      {/* Section B */}
      <SectionBox label="Work Done During the Period" letter="B" delay={80}>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px]" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#D5E8F0" }}>
                {["Task Description", "Date From", "Date To"].map(h => (
                  <th
                    key={h}
                    className="text-left text-[11px] font-semibold tracking-wide uppercase py-2 px-3 text-[var(--ink-dim)]"
                    style={{ borderBottom: "1px solid rgba(15,25,35,0.12)" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result!.section_b_rows.map((row, i) => (
                <tr
                  key={i}
                  style={{ borderBottom: "1px solid rgba(15,25,35,0.07)" }}
                  className={row.is_leave ? "opacity-60" : ""}
                >
                  <td className="py-2 px-3 text-[var(--ink)] leading-relaxed">
                    {row.is_leave && (
                      <span className="tag tag-warning mr-1.5" style={{ fontSize: "9.5px" }}>Leave</span>
                    )}
                    {row.task_description}
                  </td>
                  <td className="py-2 px-3 text-[var(--ink-muted)] whitespace-nowrap font-mono" style={{ fontSize: "11.5px" }}>
                    {row.date_from}
                  </td>
                  <td className="py-2 px-3 text-[var(--ink-muted)] whitespace-nowrap font-mono" style={{ fontSize: "11.5px" }}>
                    {row.date_to}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionBox>

      {/* Section C */}
      <SectionBox label="Reflection" letter="C" delay={160}>
        <div className="text-[13px] text-[var(--ink)] leading-relaxed whitespace-pre-wrap">
          {result!.section_c.split("\n").map((line, i) => {
            const isSubheading = ["Key Achievements", "Main Challenge Faced", "What I Did Well", "Areas for Improvement"]
              .some(h => line.trim().toLowerCase().startsWith(h.toLowerCase()));
            return (
              <p key={i} className={isSubheading ? "font-semibold mt-3 mb-0.5 first:mt-0" : "mb-1"}>
                {line}
              </p>
            );
          })}
        </div>
      </SectionBox>

      {/* Stats + Download */}
      <div
        className="flex items-center justify-between p-3 rounded-[5px] animate-fade-up animate-d4"
        style={{ background: "var(--paper-warm)", border: "1px solid var(--border)" }}
      >
        <div className="space-y-0.5">
          <p className="text-[11px] font-medium text-[var(--ink-dim)]">Generation complete</p>
          {/* <p className="font-mono text-[10.5px] text-[var(--ink-muted)]">
            {result!.token_usage.total_tokens} tokens · ≈${result!.token_usage.estimated_cost_usd.toFixed(4)}
          </p> */}
        </div>
        <div className="flex gap-2">
          {result!.storage_info?.presigned_url && (
            <a
              href={result!.storage_info.presigned_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-[11.5px]"
            >
              S3 Link
            </a>
          )}
          <button onClick={handleDownload} className="btn-accent text-[12.5px] flex items-center gap-1.5">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M6.5 1.5v7M4 6.5l2.5 2.5 2.5-2.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M1.5 10.5h10" stroke="white" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            Download .docx
          </button>
        </div>
      </div>
    </div>
  );
}
