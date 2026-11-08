"use client";

import React, { useEffect, useState, useCallback } from "react";
import { getCandidateReportApi, downloadAnalyticsCsv } from "@/lib/api/analytics";
import { CandidatePerformanceDetailResponse } from "@/types/analytics";

interface CandidatePerformanceModalProps {
  candidateId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function CandidatePerformanceModal({
  candidateId,
  isOpen,
  onClose,
}: CandidatePerformanceModalProps) {
  const [report, setReport] = useState<CandidatePerformanceDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const loadReport = useCallback(async () => {
    if (!candidateId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getCandidateReportApi(candidateId);
      if (res.success && res.data) {
        setReport(res.data);
      } else {
        setError(res.error?.message || "Failed to load candidate performance report.");
      }
    } catch {
      setError("An unexpected error occurred while fetching candidate report.");
    }
    setLoading(false);
  }, [candidateId]);

  useEffect(() => {
    let ignore = false;
    async function fetchReport() {
      if (!isOpen || !candidateId) return;
      try {
        const res = await getCandidateReportApi(candidateId);
        if (!ignore) {
          if (res.success && res.data) {
            setReport(res.data);
          } else {
            setError(res.error?.message || "Failed to load candidate performance report.");
          }
          setLoading(false);
        }
      } catch {
        if (!ignore) {
          setError("Failed to load candidate report.");
          setLoading(false);
        }
      }
    }

    if (isOpen) {
      fetchReport();
    }
    return () => {
      ignore = true;
    };
  }, [isOpen, candidateId]);

  const handleExportCsv = async () => {
    if (!report || !candidateId) return;
    setExporting(true);
    await downloadAnalyticsCsv(
      `/analytics/instructor/candidates/${candidateId}/export`,
      `candidate_${report.full_name.replace(/\s+/g, "_")}_report.csv`
    );
    setExporting(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-5xl bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-800 px-6 py-4 bg-neutral-950/60">
          <div>
            <span className="text-xs font-semibold tracking-wider text-orange-400 uppercase">
              Candidate Performance Audit
            </span>
            <h2 className="text-xl font-bold text-neutral-100">
              {report ? report.full_name : "Candidate Report"}
            </h2>
            {report && (
              <p className="text-xs text-neutral-400">{report.email} • Joined {new Date(report.joined_at).toLocaleDateString()}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleExportCsv}
              disabled={exporting || loading || !report}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded-lg transition disabled:opacity-50"
            >
              <svg className="w-4 h-4 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {exporting ? "Exporting..." : "Export Report CSV"}
            </button>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-200 text-lg px-2 py-1 rounded transition"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[80vh] overflow-y-auto space-y-6">
          {loading ? (
            <div className="py-20 text-center text-neutral-400 text-sm">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-orange-500 mb-2"></div>
              <p>Aggregating student mastery records and submission history...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-sm flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={loadReport}
                className="px-3 py-1 bg-red-800/60 hover:bg-red-700 text-white rounded text-xs transition"
              >
                Retry
              </button>
            </div>
          ) : report ? (
            <>
              {/* Summary KPIs Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Assessments Completed</span>
                  <div className="text-2xl font-bold text-neutral-100 mt-1">
                    {report.assessments_completed} <span className="text-sm font-normal text-neutral-500">/ {report.assessments_attempted} attempted</span>
                  </div>
                </div>

                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Average Score</span>
                  <div className="text-2xl font-bold text-orange-400 mt-1">
                    {report.average_score_pct.toFixed(1)}%
                  </div>
                </div>

                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Best Score</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    {report.best_score_pct.toFixed(1)}%
                  </div>
                </div>

                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Code Submissions</span>
                  <div className="text-2xl font-bold text-cyan-400 mt-1">
                    {report.submissions.length}
                  </div>
                </div>
              </div>

              {/* Strengths & Weaknesses Badges */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-emerald-950/20 border border-emerald-900/40 p-4 rounded-xl">
                  <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <span>🌟</span> Demonstrated Strengths (Score ≥ 70%)
                  </h4>
                  {report.strengths.length === 0 ? (
                    <p className="text-xs text-neutral-400 italic">No topic mastery ≥ 70% recorded yet.</p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {report.strengths.map((s) => (
                        <span key={s} className="px-2.5 py-1 bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 rounded-lg text-xs font-medium">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="bg-rose-950/20 border border-rose-900/40 p-4 rounded-xl">
                  <h4 className="text-xs font-bold text-rose-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <span>⚠️</span> Areas for Growth (Score &lt; 50%)
                  </h4>
                  {report.weaknesses.length === 0 ? (
                    <p className="text-xs text-neutral-400 italic">No critical topic weaknesses identified.</p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {report.weaknesses.map((w) => (
                        <span key={w} className="px-2.5 py-1 bg-rose-900/40 border border-rose-700/50 text-rose-300 rounded-lg text-xs font-medium">
                          {w}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Topic Mastery Section (Phase 6 Integration) */}
              <div className="bg-neutral-950/40 border border-neutral-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
                    <span>🧠</span> Topic Mastery Progression
                  </h3>
                  <span className="text-xs text-neutral-500">Derived from adaptive mastery model</span>
                </div>
                {report.topic_mastery.length === 0 ? (
                  <p className="text-xs text-neutral-500 italic text-center py-6">
                    Candidate has not generated topic mastery data yet.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {report.topic_mastery.map((tm) => (
                      <div key={tm.topic} className="bg-neutral-900/60 border border-neutral-800/80 p-3.5 rounded-lg space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-neutral-200 text-xs">{tm.topic}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            tm.mastery_level === "ADVANCED"
                              ? "bg-purple-950 text-purple-300 border border-purple-800"
                              : tm.mastery_level === "PROFICIENT"
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                              : tm.mastery_level === "DEVELOPING"
                              ? "bg-amber-950 text-amber-300 border border-amber-800"
                              : "bg-neutral-800 text-neutral-400"
                          }`}>
                            {tm.mastery_level}
                          </span>
                        </div>
                        <div className="space-y-1">
                          <div className="flex justify-between text-[11px] text-neutral-400">
                            <span>Mastery Score: <b className="text-orange-400">{tm.mastery_score.toFixed(1)}%</b></span>
                            <span>Solved: {tm.questions_solved}/{tm.questions_attempted} ({tm.success_rate.toFixed(1)}%)</span>
                          </div>
                          <div className="w-full h-2 bg-neutral-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                tm.mastery_score >= 70
                                  ? "bg-emerald-500"
                                  : tm.mastery_score >= 40
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${Math.min(tm.mastery_score, 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-neutral-500 pt-1 border-t border-neutral-800/60">
                          <span>Confidence: <span className="text-neutral-400">{tm.confidence_level}</span></span>
                          <span>Trend: <span className="text-neutral-400">{tm.trend}</span></span>
                          <span>Next Difficulty: <span className="text-orange-400">{tm.recommended_difficulty}</span></span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Difficulty Breakdown Grid */}
              <div className="bg-neutral-950/40 border border-neutral-800 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                  <span>📈</span> Performance by Problem Difficulty
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  {(["EASY", "MEDIUM", "HARD"] as const).map((diff) => {
                    const item = report.difficulty_breakdown[diff] || { attempted: 0, solved: 0, success_rate: 0 };
                    return (
                      <div key={diff} className="bg-neutral-900/60 border border-neutral-800 p-3.5 rounded-lg text-center">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          diff === "EASY"
                            ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/50"
                            : diff === "MEDIUM"
                            ? "bg-amber-950/60 text-amber-400 border border-amber-800/50"
                            : "bg-rose-950/60 text-rose-400 border border-rose-800/50"
                        }`}>
                          {diff}
                        </span>
                        <div className="text-xl font-bold text-neutral-100 mt-2">
                          {item.solved} <span className="text-xs text-neutral-500 font-normal">/ {item.attempted} solved</span>
                        </div>
                        <div className="text-xs text-orange-400 font-medium mt-1">
                          {item.success_rate.toFixed(1)}% success
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Submissions History Table */}
              <div className="bg-neutral-950/40 border border-neutral-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-neutral-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-neutral-200">
                    Recent Code Submissions ({report.submissions.length})
                  </h3>
                  <span className="text-[11px] text-neutral-500">Evaluation summaries & quality diagnostics</span>
                </div>
                {report.submissions.length === 0 ? (
                  <div className="py-10 text-center text-xs text-neutral-500">
                    No submissions found for this candidate.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-neutral-900/80 text-neutral-400 font-medium border-b border-neutral-800">
                        <tr>
                          <th className="px-4 py-3">Question</th>
                          <th className="px-4 py-3">Language</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Score</th>
                          <th className="px-4 py-3">Test Cases</th>
                          <th className="px-4 py-3">Static / AI Diagnostics</th>
                          <th className="px-4 py-3 text-right">Submitted</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800/60 text-neutral-300">
                        {report.submissions.map((sub) => (
                          <tr key={sub.submission_id} className="hover:bg-neutral-800/30 transition">
                            <td className="px-4 py-3">
                              <div className="font-semibold text-neutral-100">{sub.question_title}</div>
                              <div className="text-[10px] text-neutral-500">
                                {sub.topic} • {sub.difficulty}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-neutral-300 font-mono text-[11px]">
                              {sub.language}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  sub.status === "ACCEPTED"
                                    ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/50"
                                    : sub.status === "WRONG_ANSWER"
                                    ? "bg-rose-950/60 text-rose-400 border border-rose-800/50"
                                    : "bg-amber-950/60 text-amber-400 border border-amber-800/50"
                                }`}
                              >
                                {sub.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-semibold text-neutral-100">
                              {sub.score} / {sub.max_score}
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-neutral-300">
                                {sub.test_cases_passed} / {sub.total_test_cases} passed
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div className="text-[11px] text-neutral-300">
                                {sub.static_summary ? (
                                  <span className="text-neutral-400">{sub.static_summary}</span>
                                ) : (
                                  <span className="text-neutral-600">No static warnings</span>
                                )}
                              </div>
                              {sub.ai_quality_score !== null && (
                                <div className="text-[10px] text-purple-400 mt-0.5">
                                  AI Code Quality: {sub.ai_quality_score}/100
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right text-neutral-500 text-[11px]">
                              {new Date(sub.submitted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
