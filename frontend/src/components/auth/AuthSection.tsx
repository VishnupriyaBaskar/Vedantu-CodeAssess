"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";

export function AuthSection() {
  const { user, isAuthenticated, login, register, logout, isLoading } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Sanitize display name to remove any internal development prefixes
  const cleanDisplayName = (name?: string) => {
    if (!name) return "Candidate";
    return name.replace(/^(Stage\s*\d+\s*|Sprint\s*\d+\s*)/i, "").trim() || name;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setSubmitting(true);

    if (mode === "login") {
      const res = await login({ email, password });
      if (!res.success) {
        setErrorMessage(res.error || "Authentication failed. Please verify your credentials.");
      } else {
        setSuccessMessage("Signed in successfully.");
        setPassword("");
      }
    } else {
      const res = await register({ full_name: fullName, email, password });
      if (!res.success) {
        setErrorMessage(res.error || "Registration failed. Please check the requirements.");
      } else {
        setSuccessMessage("Account created successfully. Welcome to Vedantu Assessment Platform!");
        setPassword("");
      }
    }
    setSubmitting(false);
  };

  return (
    <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 sm:p-7 shadow-sm transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-5 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
            {isAuthenticated ? "Authenticated Session" : "Candidate & Evaluator Access"}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {isAuthenticated
              ? "Your session is authenticated and active. Select a module below to proceed."
              : "Sign in with your registered email and password to access coding assessments and results."}
          </p>
        </div>
        {isAuthenticated && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Active Session
          </span>
        )}
      </div>

      {isAuthenticated && user ? (
        /* Authenticated Session Card */
        <div className="space-y-4">
          <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-5 border border-slate-200 dark:border-slate-700/80">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-11 h-11 rounded-xl bg-orange-100 text-orange-700 dark:bg-orange-950/70 dark:text-orange-300 font-bold text-base flex items-center justify-center border border-orange-200 dark:border-orange-800">
                  {cleanDisplayName(user.full_name).charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Authenticated User
                  </p>
                  <p className="text-base font-bold text-slate-900 dark:text-white">
                    {cleanDisplayName(user.full_name)}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                    {user.email}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {user.roles.map((role) => (
                  <span
                    key={role}
                    className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-bold tracking-wide bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shadow-sm"
                  >
                    {role}
                  </span>
                ))}
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Account Active
                </span>
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-1">
            <button
              onClick={() => logout()}
              disabled={isLoading}
              className="px-4 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-xl transition border border-slate-200 dark:border-slate-700"
            >
              Sign Out
            </button>
          </div>
        </div>
      ) : (
        /* Sign In / Registration Form Card */
        <div className="max-w-md mx-auto">
          {/* Segmented Mode Switcher */}
          <div className="flex p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl mb-6 border border-slate-200/80 dark:border-slate-700/80">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                mode === "login"
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                mode === "register"
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              Register as Candidate
            </button>
          </div>

          {errorMessage && (
            <div className="mb-4 p-3.5 text-xs bg-rose-50 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800 rounded-xl">
              {errorMessage}
            </div>
          )}

          {successMessage && (
            <div className="mb-4 p-3.5 text-xs bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 rounded-xl">
              {successMessage}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Full Legal Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Rohan Sharma"
                  className="w-full px-3.5 py-2.5 text-sm bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 dark:text-white transition"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full px-3.5 py-2.5 text-sm bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 dark:text-white transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2.5 text-sm bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 dark:text-white transition"
              />
              {mode === "register" && (
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5">
                  Minimum 8 characters with at least one uppercase letter, one digit, and one special symbol.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-2 py-2.5 px-4 bg-orange-600 hover:bg-orange-700 active:bg-orange-800 text-white font-bold text-sm rounded-xl transition-all shadow-sm shadow-orange-500/20 disabled:opacity-50"
            >
              {submitting
                ? "Verifying..."
                : mode === "login"
                ? "Sign In to Portal"
                : "Create Candidate Account"}
            </button>
          </form>
        </div>
      )}
    </section>
  );
}
