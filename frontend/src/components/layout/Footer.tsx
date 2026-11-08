import React from "react";

export function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-6 mt-auto transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 dark:text-slate-400 gap-3">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-700 dark:text-slate-300">Vedantu Learning Technologies</span>
          <span>•</span>
          <span>Online Coding Assessment Platform</span>
        </div>
        <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Evaluation Engines Active
          </span>
          <span>•</span>
          <span>Automated Sandboxed Grading</span>
        </div>
      </div>
    </footer>
  );
}
