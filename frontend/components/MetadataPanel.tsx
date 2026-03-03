"use client";

import { StudentMetadata, UserProfile } from "@/lib/api";

interface Props {
  value: Partial<StudentMetadata>;
  onChange: (v: Partial<StudentMetadata>) => void;
  profile: UserProfile | null;
  onEditProfile?: () => void;
}

const entryFields: {
  key: keyof StudentMetadata;
  label: string;
  placeholder: string;
  hint?: string;
  type?: string;
}[] = [
  { key: "entry_name",      label: "Entry Name",      placeholder: "LB-3",                        hint: "Name or label for this submission" },
  { key: "period_start",    label: "Period Start",    placeholder: "09/02/2026",  hint: "DD/MM/YYYY" },
  { key: "period_end",      label: "Period End",      placeholder: "21/02/2026",  hint: "DD/MM/YYYY" },
  { key: "submission_date", label: "Submission Date", placeholder: "21/02/2026",  hint: "DD/MM/YYYY" },
];

export default function MetadataPanel({ value, onChange, profile, onEditProfile }: Props) {
  const handleChange = (key: keyof StudentMetadata, val: string) => {
    const updated = { ...value, [key]: val };
    onChange(updated);
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
        {onEditProfile && (
          <button onClick={onEditProfile} className="btn-secondary text-xs flex items-center gap-1.5">
            <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
              <path d="M7.5 1.5l2 2-6 6H1.5v-2l6-6z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
            </svg>
            Edit profile
          </button>
        )}
      </div>

      {/* Profile fields — read-only (from Supabase) */}
      {profile && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 mb-4">
          <div className="col-span-2">
            <label className="field-label">Full Name</label>
            <div className="input-field" style={{ color: "var(--ink-muted)", cursor: "default" }}>
              {profile.student_name}
            </div>
          </div>
          <div>
            <label className="field-label">Matric Number</label>
            <div className="input-field" style={{ color: "var(--ink-muted)", cursor: "default" }}>
              {profile.matric_number}
            </div>
          </div>
          <div>
            <label className="field-label">Supervisor</label>
            <div className="input-field" style={{ color: "var(--ink-muted)", cursor: "default" }}>
              {profile.supervisor}
            </div>
          </div>
          <div className="col-span-2">
            <label className="field-label">Company</label>
            <div className="input-field" style={{ color: "var(--ink-muted)", cursor: "default" }}>
              {profile.company}
            </div>
          </div>
        </div>
      )}

      <hr className="rule-line mb-4" />

      {/* Entry-specific fields — editable each submission */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-4">
        {entryFields.map(({ key, label, placeholder, hint, type }, i) => (
          <div
            key={key}
            className={`animate-fade-up animate-d${Math.min(i + 1, 5)}`}
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

      {/* Info note */}
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
          Profile info is synced from your account. Update the entry name and period dates for each new submission.
        </p>
      </div>
    </div>
  );
}
