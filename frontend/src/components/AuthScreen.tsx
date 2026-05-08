"use client";

import { useState } from "react";
import { login, register, setToken } from "@/lib/api";

export default function AuthScreen({ onAuth }: { onAuth: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = mode === "login"
        ? await login(email, password)
        : await register(email, password);
      setToken(res.access_token);
      onAuth();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: brand panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-violet-900 flex-col justify-between px-14 py-12">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-white/15 flex items-center justify-center">
            <span className="text-white text-xs font-bold tracking-tight">CP</span>
          </div>
          <span className="text-white font-semibold text-sm">CareerPilot</span>
        </div>

        <div>
          <p className="text-violet-300 text-xs font-semibold tracking-widest uppercase mb-4">
            AI job coaching platform
          </p>
          <h2 className="text-4xl font-bold text-white leading-tight mb-4">
            Your goal.<br />Your schedule.<br />Your offer.
          </h2>
          <p className="text-violet-300 text-sm leading-relaxed max-w-xs">
            Tell me your target role and timeline — I&apos;ll build your personalized plan and schedule every day around getting you that offer.
          </p>
        </div>

        <p className="text-violet-400 text-xs">
          Private &amp; confidential. Your data stays yours.
        </p>
      </div>

      {/* Right: form panel */}
      <div className="flex-1 flex items-center justify-center bg-gray-50 px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Mobile brand */}
          <div className="flex items-center gap-2.5 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-full bg-violet-700 flex items-center justify-center">
              <span className="text-white text-xs font-bold">CP</span>
            </div>
            <span className="font-semibold text-gray-900 text-sm">CareerPilot</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            {mode === "login" ? "Welcome back" : "Get started"}
          </h1>
          <p className="text-sm text-gray-500 mb-8">
            {mode === "login"
              ? "Sign in to continue your journey."
              : "Create your account — it only takes a moment."}
          </p>

          {/* Tab toggle */}
          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-6">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(null); }}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                  mode === m
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {m === "login" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent transition"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent transition"
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3.5 py-2.5">
                <span className="text-red-400 mt-0.5 shrink-0">!</span>
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-violet-700 hover:bg-violet-800 active:bg-violet-900 disabled:opacity-50 text-white rounded-lg py-2.5 text-sm font-semibold transition-colors shadow-sm mt-2"
            >
              {loading
                ? mode === "login" ? "Signing in…" : "Creating account…"
                : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <p className="text-center text-xs text-gray-400 mt-6">
            Your conversations are private and secure.
          </p>
        </div>
      </div>
    </div>
  );
}
