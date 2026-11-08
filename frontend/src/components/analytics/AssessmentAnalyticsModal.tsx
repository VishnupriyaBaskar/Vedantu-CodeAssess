"use client";

import React, { useEffect, useState, useCallback } from "react";
import { getAssessmentAnalyticsApi, downloadAnalyticsCsv } from "@/lib/api/analytics";
import { AssessmentAnalyticsResponse } from "@/types/analytics";

interface AssessmentAnalyticsModalProps {
  assessmentId: string;
  assessmentTitle: string;
  isOpen: boolean;
  onClose: () => void;
  onOpenCandidateReport?: (candidateId: string) => void;
  onOpenProctoringReview?: (assessmentId: string, assessmentTitle: string) => void;
}

export function AssessmentAnalyticsModal({
  assessmentId,
  assessmentTitle,
  isOpen,
  onClose,
  onOpenCandidateReport,
  onOpenProctoringReview,
}: AssessmentAnalyticsModalProps) {
  const [data, setData] = useState<AssessmentAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const loadData = useCallback(async () => {
    if (!assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getAssessmentAnalyticsApi(assessmentId);
      if (res.success && res.data) {
        setData(res.data);
      } else {
        setError(res.error?.message || "Failed to load assessment analytics.");
      }
    } catch {
      setError("An unexpected error occurred while loading assessment analytics.");
    }
    setLoading(false);
  }, [assessmentId]);

  useEffect(() => {
    let ignore = false;
    async function fetchAnalytics() {
      if (!isOpen || !assessmentId) return;
      try {
        const res = await getAssessmentAnalyticsApi(assessmentId);
        if (!ignore) {
          if (res.success && res.data) {
            setData(res.data);
          } else {
            setError(res.error?.message || "Failed to load assessment analytics.");
          }
          setLoading(false);
        }
      } catch {
        if (!ignore) {
          setError("Failed to load assessment analytics.");
          setLoading(false);
        }
      }
    }

    if (isOpen) {
      fetchAnalytics();
    }
    return () => {
      ignore = true;
    };
  }, [isOpen, assessmentId]);

  const handleExportCsv = async () => {
    if (!data) return;
    setExporting(true);
    await downloadAnalyticsCsv(
      `/analytics/instructor/assessments/${assessmentId}/export`,
      `assessment_${data.title.replace(/\s+/g, "_")}_results.csv`
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
              Assessment Analytics
            </span>
            <h2 className="text-xl font-bold text-neutral-100">{assessmentTitle}</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleExportCsv}
              disabled={exporting || loading || !data}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded-lg transition disabled:opacity-50"
            >
              <svg className="w-4 h-4 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {exporting ? "Exporting..." : "Export CSV"}
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
              <p>Aggregating candidate performance metrics...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-sm flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={loadData}
                className="px-3 py-1 bg-red-800/60 hover:bg-red-700 text-white rounded text-xs transition"
              >
                Retry
              </button>
            </div>
          ) : data ? (
            <>
              {/* Primary KPIs Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Attempts / Enrolled</span>
                  <div className="text-2xl font-bold text-neutral-100 mt-1">
                    {data.completed_attempts} <span className="text-sm font-normal text-neutral-500">/ {data.total_attempts} started</span>
                  </div>
                  <div className="text-xs text-neutral-400 mt-1">
                    Completion rate: <span className="text-orange-400 font-semibold">{data.completion_percentage.toFixed(1)}%</span>
                  </div>
                </div>

                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Pass Rate</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    {data.pass_percentage.toFixed(1)}%
                  </div>
                  <div className="text-xs text-neutral-400 mt-1">
                    {data.pass_count} Passed / {data.fail_count} Failed
                  </div>
                </div>

                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Average Score</span>
                  <div className="text-2xl font-bold text-cyan-400 mt-1">
                    {data.average_score_pct.toFixed(1)}%
                  </div>
                  <div className="text-xs text-neutral-400 mt-1">
                    Raw: {data.average_score.toFixed(1)} / {data.total_marks} pts
                  </div>
                </div>

                <div className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-xl">
                  <span className="text-xs text-neutral-400 font-medium">Score Extremes</span>
                  <div className="text-lg font-bold text-neutral-200 mt-1 flex items-center justify-between">
                    <span className="text-emerald-400">High: {data.highest_score}</span>
                    <span className="text-rose-400">Low: {data.lowest_score}</span>
                  </div>
                  <div className="text-xs text-neutral-400 mt-1">
                    Passing threshold: {data.passing_score} marks
                  </div>
                </div>
              </div>

              {/* Proctoring Integration Banner */}
              {data.proctoring_monitored_sessions > 0 && (
                <div className="bg-gradient-to-r from-neutral-900 to-neutral-950 border border-neutral-800 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-orange-500/10 border border-orange-500/30 flex items-center justify-center text-orange-400">
                      🛡️
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-neutral-200">
                        Proctoring Telemetry
                      </h4>
                      <p className="text-xs text-neutral-400">
                        {data.proctoring_monitored_sessions} monitored sessions, {data.proctoring_total_events} events, {data.proctoring_total_alerts} advisory alerts ({data.proctoring_pending_alerts} pending review, {data.proctoring_high_severity_alerts} high severity).
                      </p>
                    </div>
                  </div>
                  {onOpenProctoringReview && (
                    <button
                      onClick={() => onOpenProctoringReview(data.assessment_id, data.title)}
                      className="px-3 py-1.5 bg-orange-600/20 hover:bg-orange-600/30 text-orange-400 border border-orange-500/30 rounded-lg text-xs font-medium transition"
                    >
                      Open Proctoring Review Drawer
                    </button>
                  )}
                </div>
              )}

              {/* Charts Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Score Distribution Chart */}
                <div className="bg-neutral-950/40 border border-neutral-800 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                    <span>📊</span> Score Distribution
                  </h3>
                  <div className="space-y-3">
                    {data.score_distribution.map((bucket) => (
                      <div key={bucket.range_label} className="space-y-1">
                        <div className="flex justify-between text-xs text-neutral-300">
                          <span>{bucket.range_label}</span>
                          <span className="font-semibold text-orange-400">
                            {bucket.count} candidate{bucket.count !== 1 ? "s" : ""} ({bucket.percentage.toFixed(1)}%)
                          </span>
                        </div>
                        <div className="w-full h-2.5 bg-neutral-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-orange-500 to-amber-400 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(bucket.percentage, 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Topic Breakdown */}
                <div className="bg-neutral-950/40 border border-neutral-800 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                    <span>🎯</span> Topic Performance
                  </h3>
                  {data.topic_breakdown.length === 0 ? (
                    <p className="text-xs text-neutral-500 italic py-6 text-center">
                      No topic performance recorded yet.
                    </p>
                  ) : (
                    <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
                      {data.topic_breakdown.map((t) => (
                        <div key={t.topic} className="space-y-1">
                          <div className="flex justify-between text-xs text-neutral-300">
                            <span className="font-medium">{t.topic}</span>
                            <span className="text-neutral-400">
                              {t.average_score_pct.toFixed(1)}% ({t.total_attempts} attempts)
                            </span>
                          </div>
                          <div className="w-full h-2.5 bg-neutral-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                t.average_score_pct >= 70
                                  ? "bg-emerald-500"
                                  : t.average_score_pct >= 40
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${Math.min(t.average_score_pct, 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Candidate Performance Table */}
              <div className="bg-neutral-950/40 border border-neutral-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-neutral-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-neutral-200">
                    Candidate Submissions & Results ({data.candidates.length})
                  </h3>
                  <span className="text-xs text-neutral-400">Sorted by score</span>
                </div>
                {data.candidates.length === 0 ? (
                  <div className="py-10 text-center text-xs text-neutral-500">
                    No candidates have attempted this assessment yet.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-neutral-900/80 text-neutral-400 font-medium border-b border-neutral-800">
                        <tr>
                          <th className="px-4 py-3">Candidate</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Score</th>
                          <th className="px-4 py-3">Percentage</th>
                          <th className="px-4 py-3">Outcome</th>
                          <th className="px-4 py-3">Proctoring Alerts</th>
                          <th className="px-4 py-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-800/60 text-neutral-300">
                        {data.candidates.map((c) => (
                          <tr key={c.candidate_id + (c.attempt_id || "")} className="hover:bg-neutral-800/30 transition">
                            <td className="px-4 py-3">
                              <div className="font-semibold text-neutral-100">{c.full_name}</div>
                              <div className="text-[11px] text-neutral-500">{c.email}</div>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  c.status === "COMPLETED"
                                    ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/50"
                                    : c.status === "IN_PROGRESS"
                                    ? "bg-amber-950/60 text-amber-400 border border-amber-800/50"
                                    : "bg-neutral-800 text-neutral-400"
                                }`}
                              >
                                {c.status || "NOT_STARTED"}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-medium">
                              {typeof c.score === "number" ? `${c.score.toFixed(1)} / ${c.max_score || 100}` : "—"}
                            </td>
                            <td className="px-4 py-3 font-bold text-neutral-100">
                              {typeof c.score_pct === "number" ? `${c.score_pct.toFixed(1)}%` : "—"}
                            </td>
                            <td className="px-4 py-3">
                              {typeof c.passed === "boolean" ? (
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    c.passed
                                      ? "bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
                                      : "bg-rose-950/80 text-rose-300 border border-rose-700/50"
                                  }`}
                                >
                                  {c.passed ? "PASSED" : "FAILED"}
                                </span>
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="px-4 py-3">
                              {c.proctoring_alerts_count > 0 ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-orange-950/60 border border-orange-800/50 text-orange-400 text-[10px] font-semibold">
                                  ⚠️ {c.proctoring_alerts_count} alert{c.proctoring_alerts_count !== 1 ? "s" : ""}
                                </span>
                              ) : (
                                <span className="text-neutral-500 text-[11px]">Clean</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {onOpenCandidateReport && (
                                <button
                                  onClick={() => onOpenCandidateReport(c.candidate_id)}
                                  className="px-2.5 py-1 text-[11px] font-medium bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded transition"
                                >
                                  Audit Report
                                </button>
                              )}
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
