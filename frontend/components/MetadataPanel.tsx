"use client";

import { useEffect, useState } from "react";
import { StudentMetadata, saveMetadata, loadMetadata } from "@/lib/api";

interface Props {
  value: Partial<StudentMetadata>;
  onChange: (v: Partial<StudentMetadata>) => void;
}

const fields: {
  key: keyof StudentMetadata;
  label: string;
  placeholder: string;
  hint?: string;
  type?: string;
}[] = [
  { key: "student_name",   label: "Full Name",        placeholder: "Tan Wei Ming" },
  { key: "matric_number",  label: "Matric Number",     placeholder: "U2012345B" },
  { key: "company",        label: "Company",           placeholder: "TechCorp Singapore Pte Ltd" },
  { key: "supervisor",     label: "Supervisor",        placeholder: "John Chen" },
  { key: "entry_number",   label: "Entry No.",         placeholder: "3", type: "number", hint: "Which logbook submission is this?" },
  { key: "period_start",   label: "Period Start",      placeholder: "09/02/2026", hint: "DD/MM/YYYY" },
  { key: "period_end",     label: "Period End",        placeholder: "21/02/2026", hint: "DD/MM/YYYY" },
  { key: "submission_date",label: "Submission Date",   placeholder: "21/02/2026", hint: "DD/MM/YYYY" },
];

export default function MetadataPanel({ value, onChange }: Props) {
  const [saved, setSaved] = useState(false);

  const handleChange = (key: keyof StudentMetadata, val: string) => {
    const updated = { ...value, [key]: key === "entry_number" ? Number(val) : val };
    onChange(updated);
  };

  const handleSave = () => {
    saveMetadata(value as StudentMetadata);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <p className="section-letter mb-0.5">Student Info</p>
          <h2 className="font-display text-lg font-semibold text-[var(--ink)]" style={{ lineHeight: 1.2 }}>
            Metadata
          </h2>
        </div>
        <button
          onClick={handleSave}
          className="btn-secondary text-xs flex items-center gap-1.5"
        >
          {saved ? (
            <>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 6l3 3 5-5" stroke="var(--success)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Saved
            </>
          ) : (
            <>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 6l1.5 1.5L10 3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Save info
            </>
          )}
        </button>
      </div>

      {/* Fields grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-4">
        {fields.map(({ key, label, placeholder, hint, type }, i) => (
          <div
            key={key}
            className={`animate-fade-up animate-d${Math.min(i + 1, 5)} ${
              key === "company" || key === "student_name" ? "col-span-2" : ""
            }`}
          >
            <label className="field-label">
              {label}
              {hint && (
                <span className="ml-1 font-normal normal-case text-[10px] text-[var(--ink-muted)] opacity-70">
                  — {hint}
                </span>
              )}
            </label>
            <input
              type={type || "text"}
              className="input-field"
              placeholder={placeholder}
              value={String(value[key] ?? "")}
              onChange={(e) => handleChange(key, e.target.value)}
              min={type === "number" ? 1 : undefined}
              max={type === "number" ? 99 : undefined}
            />
          </div>
        ))}
      </div>

      {/* Persistent note */}
      <div
        className="mt-5 px-3 py-2.5 rounded-[4px] flex gap-2.5"
        style={{ background: "var(--accent-light)", border: "1px solid rgba(196,120,58,0.2)" }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
          <circle cx="7" cy="7" r="6" stroke="var(--accent)" strokeWidth="1.2"/>
          <path d="M7 6.5v3.5" stroke="var(--accent)" strokeWidth="1.3" strokeLinecap="round"/>
          <circle cx="7" cy="4.5" r="0.7" fill="var(--accent)"/>
        </svg>
        <p className="text-[11.5px] text-[var(--accent-dim)] leading-relaxed">
          Student info and internship objective are saved locally and pre-filled on your next visit.
        </p>
      </div>
    </div>
  );
}
