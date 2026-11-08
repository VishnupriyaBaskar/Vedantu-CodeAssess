"use client";

import React from "react";
import { useAuth } from "@/context/AuthContext";

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();

  // Clean any internal stage prefix from legacy test user names for display
  const cleanDisplayName = (name?: string) => {
    if (!name) return "Candidate";
    return name.replace(/^(Stage\s*\d+\s*|Sprint\s*\d+\s*)/i, "").trim() || name;
  };

  const displayName = user ? cleanDisplayName(user.full_name) : "";
  const initial = displayName ? displayName.charAt(0).toUpperCase() : "U";

  return (
    <header className="border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md sticky top-0 z-50 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center font-extrabold text-white text-lg shadow-sm shadow-orange-500/20">
            V
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-bold text-base sm:text-lg text-slate-900 dark:text-white tracking-tight">
                Vedantu
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-orange-50 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300 border border-orange-200/60 dark:border-orange-800/60">
                CodeAssess
              </span>
            </div>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 hidden sm:block -mt-0.5">
              Enterprise Coding Assessment Platform
            </span>
          </div>
        </div>

        {/* Right navigation / User context */}
        <div className="flex items-center space-x-3">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 flex items-center justify-center text-xs font-bold text-slate-700 dark:text-slate-200">
                  {initial}
                </div>
                <div className="hidden sm:flex flex-col text-left">
                  <span className="text-xs font-bold text-slate-900 dark:text-white leading-tight">
                    {displayName}
                  </span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono leading-tight">
                    {user.email}
                  </span>
                </div>
              </div>

              {/* Roles */}
              <div className="flex items-center gap-1.5">
                {user.roles.map((role) => (
                  <span
                    key={role}
                    className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold tracking-wide bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                  >
                    {role}
                  </span>
                ))}
              </div>

              <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 mx-1 hidden sm:block" />

              <button
                onClick={() => logout()}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-lg transition-colors"
                title="Sign out of your session"
              >
                Sign out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Assessment System Online
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
