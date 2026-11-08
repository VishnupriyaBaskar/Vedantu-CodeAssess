"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  getAssessmentAlertsApi,
  getAssessmentProctoringOverviewApi,
  getAttemptProctoringReportApi,
  reviewProctoringAlertApi,
} from "@/lib/api/proctoring";
import {
  AssessmentProctoringOverviewResponse,
  AttemptProctoringReportResponse,
  CandidateProctoringSummary,
  ProctoringAlertResponse,
} from "@/types/proctoring";

interface InstructorProctoringModalProps {
  assessmentId: string;
  assessmentTitle: string;
  isOpen: boolean;
  onClose: () => void;
}

export function InstructorProctoringModal({
  assessmentId,
  assessmentTitle,
  isOpen,
  onClose,
}: InstructorProctoringModalProps) {
  const [overview, setOverview] = useState<AssessmentProctoringOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detailed Candidate Audit State
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [attemptReport, setAttemptReport] = useState<AttemptProctoringReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  // Alert Review Form State
  const [editingAlertId, setEditingAlertId] = useState<string | null>(null);
  const [reviewStatus, setReviewStatus] = useState<"PENDING" | "REVIEWED" | "CLEARED" | "ESCALATED">("REVIEWED");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

  const loadOverview = useCallback(async () => {
    if (!assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getAssessmentProctoringOverviewApi(assessmentId);
      if (res.success && res.data) {
        setOverview(res.data);
      } else {
        setError(res.error?.message || "Failed to load proctoring data.");
      }
    } catch {
      setError("An unexpected error occurred while fetching proctoring telemetry.");
    }
    setLoading(false);
  }, [assessmentId]);

  useEffect(() => {
    let ignore = false;
    async function fetchData() {
      if (!isOpen || !assessmentId) return;
      try {
        const res = await getAssessmentProctoringOverviewApi(assessmentId);
        if (!ignore) {
          if (res.success && res.data) {
            setOverview(res.data);
          } else {
            setError(res.error?.message || "Failed to load proctoring data.");
          }
          setLoading(false);
        }
      } catch {
        if (!ignore) {
          setError("An unexpected error occurred while fetching proctoring telemetry.");
          setLoading(false);
        }
      }
    }

    if (isOpen) {
      fetchData();
    }

    return () => {
      ignore = true;
    };
  }, [isOpen, assessmentId]);

  const handleOpenAttemptAudit = async (attemptId: string) => {
    setSelectedAttemptId(attemptId);
    setReportLoading(true);
    try {
      const res = await getAttemptProctoringReportApi(attemptId);
      if (res.success && res.data) {
        setAttemptReport(res.data);
      } else {
        alert(res.error?.message || "Failed to load attempt proctoring audit report.");
      }
    } catch {
      alert("Error fetching attempt proctoring report.");
    }
    setReportLoading(false);
  };

  const handleStartReview = (alert: ProctoringAlertResponse) => {
    setEditingAlertId(alert.id);
    setReviewStatus(alert.review_status === "PENDING" ? "REVIEWED" : alert.review_status);
    setReviewNotes(alert.review_notes || "");
  };

  const handleSubmitReview = async (alertId: string) => {
    setReviewSubmitting(true);
    try {
      const res = await reviewProctoringAlertApi(alertId, {
        review_status: reviewStatus,
        review_notes: reviewNotes,
      });
      if (res.success && res.data) {
        // Update local report alerts
        if (attemptReport) {
          setAttemptReport({
            ...attemptReport,
            alerts: attemptReport.alerts.map((a) => (a.id === alertId ? res.data! : a)),
          });
        }
        setEditingAlertId(null);
        await loadOverview();
      } else {
        alert(res.error?.message || "Failed to submit alert review.");
      }
    } catch {
      alert("Error submitting alert review.");
    }
    setReviewSubmitting(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-fade-in overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl w-full max-w-5xl my-auto shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Assessment Integrity & Proctoring Audit
              </h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Exam: <span className="font-semibold text-slate-700 dark:text-slate-300">{assessmentTitle}</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {loading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-xs text-slate-500">Loading proctoring telemetry...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-700 dark:text-rose-300">
              {error}
            </div>
          ) : overview ? (
            <>
              {/* Telemetry KPI Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Candidates</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{overview.total_candidates}</p>
                </div>
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Monitored</p>
                  <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{overview.monitored_sessions}</p>
                </div>
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Flagged</p>
                  <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{overview.flagged_candidates}</p>
                </div>
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Alerts</p>
                  <p className="text-2xl font-bold text-orange-600 dark:text-orange-400 mt-1">{overview.total_alerts}</p>
                </div>
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">High Severity</p>
                  <p className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">{overview.high_severity_alerts}</p>
                </div>
              </div>

              {/* Candidates Overview Table */}
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Candidate Session Audits
                </h3>

                {overview.candidates.length === 0 ? (
                  <p className="text-xs text-slate-500 py-6 text-center">No candidate attempts have been initiated yet.</p>
                ) : (
                  <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-100 dark:bg-slate-800/70 text-slate-600 dark:text-slate-300 font-semibold uppercase text-[10px] tracking-wider">
                        <tr>
                          <th className="py-3 px-4">Candidate</th>
                          <th className="py-3 px-3">Attempt</th>
                          <th className="py-3 px-3 text-center">Tab Switches</th>
                          <th className="py-3 px-3 text-center">Fullscreen Exits</th>
                          <th className="py-3 px-3 text-center">Window Blurs</th>
                          <th className="py-3 px-3 text-center">Alerts</th>
                          <th className="py-3 px-3 text-center">Review</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                        {overview.candidates.map((c) => (
                          <tr
                            key={c.attempt_id}
                            className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                          >
                            <td className="py-3 px-4 font-medium text-slate-900 dark:text-white">
                              <div>{c.full_name}</div>
                              <div className="text-[10px] text-slate-400">{c.email}</div>
                            </td>
                            <td className="py-3 px-3">
                              <span
                                className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  c.attempt_status === "COMPLETED"
                                    ? "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                                    : "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400"
                                }`}
                              >
                                {c.attempt_status}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-center font-semibold">{c.tab_switch_count}</td>
                            <td className="py-3 px-3 text-center font-semibold">{c.fullscreen_exit_count}</td>
                            <td className="py-3 px-3 text-center font-semibold">{c.window_blur_count}</td>
                            <td className="py-3 px-3 text-center">
                              {c.total_alerts > 0 ? (
                                <span
                                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                    c.high_severity_alerts > 0
                                      ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
                                      : "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
                                  }`}
                                >
                                  {c.total_alerts} {c.total_alerts === 1 ? "Alert" : "Alerts"}
                                </span>
                              ) : (
                                <span className="text-slate-400 text-[10px]">Clean</span>
                              )}
                            </td>
                            <td className="py-3 px-3 text-center">
                              <span
                                className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  c.review_status === "CLEARED"
                                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                                    : c.review_status === "ESCALATED"
                                    ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
                                    : c.review_status === "REVIEWED"
                                    ? "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300"
                                    : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                                }`}
                              >
                                {c.review_status}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                type="button"
                                onClick={() => handleOpenAttemptAudit(c.attempt_id)}
                                className="px-3 py-1 rounded-xl bg-orange-50 hover:bg-orange-100 text-orange-700 dark:bg-orange-950/50 dark:hover:bg-orange-900/50 dark:text-orange-300 text-xs font-semibold transition-colors"
                              >
                                View Audit
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Detailed Attempt Audit Drawer */}
              {selectedAttemptId && (
                <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 space-y-5 animate-fade-in">
                  <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                        Detailed Audit Log: {attemptReport?.candidate_name}
                      </h4>
                      <p className="text-[11px] text-slate-500">{attemptReport?.candidate_email}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedAttemptId(null)}
                      className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    >
                      Close Detail
                    </button>
                  </div>

                  {reportLoading ? (
                    <div className="py-8 text-center text-xs text-slate-500">Loading candidate audit timeline...</div>
                  ) : attemptReport ? (
                    <div className="space-y-5">
                      {/* Alerts Section */}
                      <div className="space-y-3">
                        <h5 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                          Suspicious Activity Alerts ({attemptReport.alerts.length})
                        </h5>

                        {attemptReport.alerts.length === 0 ? (
                          <p className="text-xs text-slate-400 italic">No alerts triggered during this session.</p>
                        ) : (
                          <div className="space-y-3">
                            {attemptReport.alerts.map((al) => (
                              <div
                                key={al.id}
                                className={`p-4 rounded-xl border space-y-2.5 ${
                                  al.severity === "HIGH"
                                    ? "bg-rose-50/60 dark:bg-rose-950/20 border-rose-200 dark:border-rose-900/50"
                                    : al.severity === "MEDIUM"
                                    ? "bg-amber-50/60 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/50"
                                    : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700"
                                }`}
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="flex items-center gap-2">
                                    <span
                                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                        al.severity === "HIGH"
                                          ? "bg-rose-600 text-white"
                                          : al.severity === "MEDIUM"
                                          ? "bg-amber-600 text-white"
                                          : "bg-slate-600 text-white"
                                      }`}
                                    >
                                      {al.severity}
                                    </span>
                                    <span className="font-bold text-xs text-slate-900 dark:text-white">
                                      {al.alert_category}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-[10px] font-semibold text-slate-500 uppercase">
                                      Status: {al.review_status}
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => handleStartReview(al)}
                                      className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-orange-500 text-[11px] font-semibold text-slate-700 dark:text-slate-300 transition-colors"
                                    >
                                      Review
                                    </button>
                                  </div>
                                </div>

                                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                                  {al.explanation}
                                </p>

                                {al.review_notes && (
                                  <div className="text-[11px] text-slate-500 italic border-l-2 border-slate-300 dark:border-slate-700 pl-2">
                                    Instructor Note: {al.review_notes} (by {al.reviewer_name || "Instructor"})
                                  </div>
                                )}

                                {/* Inline Review Form */}
                                {editingAlertId === al.id && (
                                  <div className="mt-3 p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 space-y-2.5 animate-fade-in">
                                    <div className="flex items-center gap-3">
                                      <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                        Update Review Status:
                                      </label>
                                      <select
                                        value={reviewStatus}
                                        onChange={(e) =>
                                          setReviewStatus(e.target.value as "PENDING" | "REVIEWED" | "CLEARED" | "ESCALATED")
                                        }
                                        className="px-2.5 py-1 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                      >
                                        <option value="REVIEWED">REVIEWED</option>
                                        <option value="CLEARED">CLEARED</option>
                                        <option value="ESCALATED">ESCALATED</option>
                                        <option value="PENDING">PENDING</option>
                                      </select>
                                    </div>
                                    <textarea
                                      value={reviewNotes}
                                      onChange={(e) => setReviewNotes(e.target.value)}
                                      placeholder="Add instructor audit notes (optional)..."
                                      className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white resize-none h-16"
                                    />
                                    <div className="flex justify-end gap-2">
                                      <button
                                        type="button"
                                        onClick={() => setEditingAlertId(null)}
                                        className="px-3 py-1 text-xs rounded-lg text-slate-500 hover:text-slate-700"
                                      >
                                        Cancel
                                      </button>
                                      <button
                                        type="button"
                                        disabled={reviewSubmitting}
                                        onClick={() => handleSubmitReview(al.id)}
                                        className="px-4 py-1 text-xs rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-semibold transition-colors"
                                      >
                                        {reviewSubmitting ? "Saving..." : "Save Status"}
                                      </button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Event Stream Timeline */}
                      <div className="space-y-3">
                        <h5 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                          Chronological Integrity Stream ({attemptReport.events.length})
                        </h5>

                        {attemptReport.events.length === 0 ? (
                          <p className="text-xs text-slate-400 italic">No events logged.</p>
                        ) : (
                          <div className="max-h-60 overflow-y-auto space-y-1.5 text-xs font-mono">
                            {attemptReport.events.map((ev) => (
                              <div
                                key={ev.id}
                                className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800"
                              >
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] text-slate-400">
                                    {new Date(ev.recorded_at).toLocaleTimeString()}
                                  </span>
                                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                                    {ev.event_type}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 text-[10px]">
                                  {ev.event_metadata && (
                                    <span className="text-slate-400">
                                      {JSON.stringify(ev.event_metadata)}
                                    </span>
                                  )}
                                  <span
                                    className={`px-1.5 py-0.5 rounded font-bold ${
                                      ev.severity === "HIGH"
                                        ? "bg-rose-100 dark:bg-rose-950 text-rose-600"
                                        : ev.severity === "MEDIUM"
                                        ? "bg-amber-100 dark:bg-amber-950 text-amber-600"
                                        : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                                    }`}
                                  >
                                    {ev.severity}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
