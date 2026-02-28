"use client";

import { useState } from "react";

interface Props {
  rawNotes: string;
  objective: string;
  challenges: string;
  achievements: string;
  onRawNotesChange: (v: string) => void;
  onObjectiveChange: (v: string) => void;
  onChallengesChange: (v: string) => void;
  onAchievementsChange: (v: string) => void;
  priorSectionA: string;
  priorSectionC: string;
  onPriorAChange: (v: string) => void;
  onPriorCChange: (v: string) => void;
}

export default function NotesPanel({
  rawNotes, objective, challenges, achievements,
  onRawNotesChange, onObjectiveChange, onChallengesChange, onAchievementsChange,
  priorSectionA, priorSectionC, onPriorAChange, onPriorCChange,
}: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const lineCount = rawNotes ? rawNotes.split("\n").filter(l => l.trim()).length : 0;
  const charCount = rawNotes.length;

  return (
    <div className="animate-fade-up animate-d1 space-y-5">
      {/* Internship Objective */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="field-label mb-0">
            Internship Objective
          </label>
          <span className="tag tag-accent text-[10px]">Persistent</span>
        </div>
        <p className="text-[11.5px] text-[var(--ink-muted)] mb-2">
          This is stored locally and reused across all entries. Edit when your objective changes.
        </p>
        <textarea
          className="input-field"
          rows={3}
          placeholder="The objective of this industrial attachment is to gain practical experience in full-stack software development…"
          value={objective}
          onChange={(e) => onObjectiveChange(e.target.value)}
        />
      </div>

      <hr className="rule-line" />

      {/* Raw Notes */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="field-label mb-0">Daily Work Notes</label>
          {lineCount > 0 && (
            <span className="font-mono text-[10.5px] text-[var(--ink-muted)]">
              {lineCount} lines · {charCount} chars
            </span>
          )}
        </div>
        <p className="text-[11.5px] text-[var(--ink-muted)] mb-2">
          Paste your raw notes. Each line should start with a date. Separate multiple tasks with commas.
        </p>
        <textarea
          className="input-field font-mono"
          rows={10}
          style={{ fontSize: "12px", lineHeight: 1.7 }}
          placeholder={`9th Feb - produced demo video for client presentation, set up GitLab CI/CD pipeline
10th Feb - configured automated testing in CI/CD, fixed pipeline failures
11th Feb - Annual Leave
12th Feb - worked on database schema optimization
13th Feb - performance testing of optimised queries, documented findings`}
          value={rawNotes}
          onChange={(e) => onRawNotesChange(e.target.value)}
        />

        {/* Format hints */}
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {[
            "9th Feb – tasks",
            "9/2/2026 – tasks",
            "Feb 9 – tasks",
            "Leave / Holiday",
          ].map(hint => (
            <span key={hint} className="tag tag-neutral font-mono" style={{ fontSize: "10px" }}>
              {hint}
            </span>
          ))}
        </div>
      </div>

      <hr className="rule-line" />

      {/* Optional fields */}
      <div className="space-y-3">
        <div>
          <label className="field-label">
            Key Achievements <span className="normal-case font-normal opacity-60">(optional)</span>
          </label>
          <textarea
            className="input-field"
            rows={2}
            placeholder="Mention specific achievements you want highlighted in Section C…"
            value={achievements}
            onChange={(e) => onAchievementsChange(e.target.value)}
          />
        </div>

        <div>
          <label className="field-label">
            Main Challenge <span className="normal-case font-normal opacity-60">(optional)</span>
          </label>
          <textarea
            className="input-field"
            rows={2}
            placeholder="Describe any significant challenges you faced during this period…"
            value={challenges}
            onChange={(e) => onChallengesChange(e.target.value)}
          />
        </div>
      </div>

      {/* Advanced: Prior entry (few-shot) */}
      <div>
        <button
          className="flex items-center gap-1.5 text-[11.5px] text-[var(--ink-muted)] hover:text-[var(--ink-dim)] transition-colors"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          <svg
            width="11" height="11" viewBox="0 0 11 11" fill="none"
            style={{ transform: showAdvanced ? "rotate(90deg)" : "rotate(0)", transition: "transform 0.2s" }}
          >
            <path d="M3.5 2L7.5 5.5L3.5 9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Advanced: Prior entry (improves style matching)
        </button>

        {showAdvanced && (
          <div className="mt-3 space-y-3 animate-fade-up">
            <p className="text-[11.5px] text-[var(--ink-muted)]">
              Paste your previous logbook's Section A and C. Claude will match the writing style exactly.
            </p>
            <div>
              <label className="field-label">Prior Section A</label>
              <textarea
                className="input-field font-mono"
                rows={4}
                style={{ fontSize: "11.5px" }}
                placeholder="During the second biweekly period…"
                value={priorSectionA}
                onChange={(e) => onPriorAChange(e.target.value)}
              />
            </div>
            <div>
              <label className="field-label">Prior Section C</label>
              <textarea
                className="input-field font-mono"
                rows={4}
                style={{ fontSize: "11.5px" }}
                placeholder="Key Achievements…"
                value={priorSectionC}
                onChange={(e) => onPriorCChange(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
