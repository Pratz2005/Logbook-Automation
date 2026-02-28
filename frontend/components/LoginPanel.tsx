"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { registerUser, UserProfile } from "@/lib/api";

interface Props {
  onLogin: (profile: UserProfile) => void;
}

type Mode = "login" | "register";

export default function LoginPanel({ onLogin }: Props) {
  const [mode, setMode] = useState<Mode>("login");
  const [matric, setMatric] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [supervisor, setSupervisor] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email: `${matric.trim()}@ntu.edu.sg`,
        password,
      });
      if (authError) throw new Error("Invalid matric number or password.");
      // Fetch profile from backend
      const token = data.session?.access_token;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/profile`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error("Could not load profile.");
      const profile: UserProfile = await res.json();
      onLogin(profile);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!matric.trim() || !password || !name.trim() || !company.trim() || !supervisor.trim()) {
      setError("All fields are required.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      const resp = await registerUser(matric.trim(), password, name.trim(), company.trim(), supervisor.trim());
      // Set Supabase session from backend-issued token
      await supabase.auth.setSession({
        access_token: resp.access_token,
        refresh_token: "",
      });
      onLogin(resp.profile);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{ minHeight: "100vh", background: "var(--paper-cool)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
    >
      <div className="section-card p-8 animate-fade-up" style={{ width: "100%", maxWidth: 420 }}>
        {/* Logo */}
        <div className="flex items-center gap-3 mb-7">
          <div
            className="flex items-center justify-center w-8 h-8 rounded"
            style={{ background: "var(--ink)", flexShrink: 0 }}
          >
            <svg width="16" height="16" viewBox="0 0 15 15" fill="none">
              <rect x="2" y="1" width="11" height="13" rx="1.5" stroke="white" strokeWidth="1.2"/>
              <path d="M5 5h5M5 7.5h5M5 10h3" stroke="white" strokeWidth="1.1" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <span className="font-display font-semibold text-[var(--ink)] text-[14px]">NTU Logbook</span>
            <span className="ml-1.5 text-[10.5px] text-[var(--ink-muted)]">Generator</span>
          </div>
        </div>

        {/* Mode tabs */}
        <div
          className="flex gap-1 p-1 rounded-[6px] mb-6"
          style={{ background: "var(--paper-warm)", border: "1px solid var(--border)" }}
        >
          {(["login", "register"] as Mode[]).map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null); }}
              className="flex-1 py-1.5 rounded-[4px] text-[12px] font-medium capitalize transition-all"
              style={
                mode === m
                  ? { background: "var(--ink)", color: "var(--paper)" }
                  : { color: "var(--ink-muted)" }
              }
            >
              {m === "login" ? "Sign in" : "Register"}
            </button>
          ))}
        </div>

        {/* Error */}
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

        {/* Login form */}
        {mode === "login" && (
          <form onSubmit={handleLogin} className="space-y-3.5">
            <div>
              <label className="field-label">Matric Number</label>
              <input
                className="input-field"
                placeholder="U2012345B"
                value={matric}
                onChange={e => setMatric(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div>
              <label className="field-label">Password</label>
              <input
                type="password"
                className="input-field"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <button type="submit" className="btn-primary w-full mt-1" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        )}

        {/* Register form */}
        {mode === "register" && (
          <form onSubmit={handleRegister} className="space-y-3.5">
            <div>
              <label className="field-label">Matric Number</label>
              <input className="input-field" placeholder="U2012345B" value={matric} onChange={e => setMatric(e.target.value)} />
            </div>
            <div>
              <label className="field-label">Password <span className="font-normal opacity-60">— min 8 chars</span></label>
              <input type="password" className="input-field" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password" />
            </div>
            <div>
              <label className="field-label">Full Name</label>
              <input className="input-field" placeholder="Tan Wei Ming" value={name} onChange={e => setName(e.target.value)} />
            </div>
            <div>
              <label className="field-label">Company</label>
              <input className="input-field" placeholder="TechCorp Singapore Pte Ltd" value={company} onChange={e => setCompany(e.target.value)} />
            </div>
            <div>
              <label className="field-label">Supervisor</label>
              <input className="input-field" placeholder="John Chen" value={supervisor} onChange={e => setSupervisor(e.target.value)} />
            </div>
            <button type="submit" className="btn-primary w-full mt-1" disabled={loading}>
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
