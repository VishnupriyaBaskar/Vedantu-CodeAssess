"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  getCohortAnalyticsApi,
  getInstructorOverviewApi,
  downloadAnalyticsCsv,
} from "@/lib/api/analytics";
import { listAssessmentsApi } from "@/lib/api/assessment";
import {
  CohortAnalyticsResponse,
  InstructorOverviewKPIs,
} from "@/types/analytics";
import { AssessmentAdmin } from "@/types/assessment";
import { AssessmentAnalyticsModal } from "./AssessmentAnalyticsModal";
import { CandidatePerformanceModal } from "./CandidatePerformanceModal";
import { InstructorProctoringModal } from "../proctoring/InstructorProctoringModal";

export function InstructorAnalyticsDashboard() {
  const [overview, setOverview] = useState<InstructorOverviewKPIs | null>(null);
  const [cohort, setCohort] = useState<CohortAnalyticsResponse | null>(null);
  const [assessments, setAssessments] = useState<AssessmentAdmin[]>([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [analyticsModalAssessment, setAnalyticsModalAssessment] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [proctoringModalAssessment, setProctoringModalAssessment] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [auditCandidateId, setAuditCandidateId] = useState<string | null>(null);

  // Export State
  const [exportingQuestions, setExportingQuestions] = useState(false);
  const [exportingAssessment, setExportingAssessment] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovRes, cohRes, assRes] = await Promise.all([
        getInstructorOverviewApi(),
        getCohortAnalyticsApi(),
        listAssessmentsApi(),
      ]);

      if (ovRes.success && ovRes.data) {
        setOverview(ovRes.data);
      }
      if (cohRes.success && cohRes.data) {
        setCohort(cohRes.data);
      }
      if (assRes.success && assRes.data) {
        setAssessments(assRes.data);
        if (assRes.data.length > 0 && !selectedAssessmentId) {
          setSelectedAssessmentId(assRes.data[0].id);
        }
      }
    } catch {
      setError("An unexpected error occurred while loading analytics data.");
    }
    setLoading(false);
  }, [selectedAssessmentId]);

  useEffect(() => {
    let ignore = false;
    async function initData() {
      try {
        const [ovRes, cohRes, assRes] = await Promise.all([
          getInstructorOverviewApi(),
          getCohortAnalyticsApi(),
          listAssessmentsApi(),
        ]);
        if (!ignore) {
          if (ovRes.success && ovRes.data) setOverview(ovRes.data);
          if (cohRes.success && cohRes.data) setCohort(cohRes.data);
          if (assRes.success && assRes.data) {
            setAssessments(assRes.data);
            if (assRes.data.length > 0) setSelectedAssessmentId(assRes.data[0].id);
          }
          setLoading(false);
        }
      } catch {
        if (!ignore) {
          setError("Failed to initialize dashboard analytics.");
          setLoading(false);
        }
      }
    }
    initData();
    return () => {
      ignore = true;
    };
  }, []);

  const handleExportQuestions = async () => {
    setExportingQuestions(true);
    await downloadAnalyticsCsv(
      "/analytics/instructor/questions/export",
      "question_bank_performance.csv"
    );
    setExportingQuestions(false);
  };

  const handleExportSelectedAssessment = async () => {
    if (!selectedAssessmentId) return;
    const selectedAss = assessments.find((a) => a.id === selectedAssessmentId);
    const title = selectedAss ? selectedAss.title.replace(/\s+/g, "_") : "assessment";
    setExportingAssessment(true);
    await downloadAnalyticsCsv(
      `/analytics/instructor/assessments/${selectedAssessmentId}/export`,
      `assessment_${title}_results.csv`
    );
    setExportingAssessment(false);
  };

  const activeAssessment = assessments.find((a) => a.id === selectedAssessmentId);

  return (
    <div className="space-y-8">
      {/* Top Header & Global Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-neutral-800">
        <div>
          <h2 className="text-2xl font-bold text-neutral-100 flex items-center gap-2">
            <span>📈</span> Instructor Analytics & Performance Insights
          </h2>
          <p className="text-sm text-neutral-400 mt-1">
            Real-time evaluation KPIs, cohort topic mastery, candidate audit trails, and proctoring telemetry.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleExportQuestions}
            disabled={exportingQuestions || loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-700 rounded-xl transition shadow-sm disabled:opacity-50"
          >
            <svg className="w-4 h-4 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {exportingQuestions ? "Exporting..." : "Export Questions CSV"}
          </button>

          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-800 rounded-xl transition"
            title="Refresh Data"
          >
            <svg className={`w-4 h-4 ${loading ? "animate-spin text-orange-400" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-24 text-center text-neutral-400 text-sm">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-orange-500 mb-3"></div>
          <p>Loading analytics and student performance metrics...</p>
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
      ) : (
        <>
          {/* Section 1: Overview KPIs Grid */}
          {overview && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <div className="bg-neutral-900/70 border border-neutral-800 p-4 rounded-xl">
                <span className="text-xs text-neutral-400 font-medium">Registered Candidates</span>
                <div className="text-2xl font-bold text-neutral-100 mt-1">
                  {overview.total_candidates}
                </div>
                <div className="text-[11px] text-neutral-500 mt-1">Enrolled students</div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800 p-4 rounded-xl">
                <span className="text-xs text-neutral-400 font-medium">Assessments</span>
                <div className="text-2xl font-bold text-orange-400 mt-1">
                  {overview.published_assessments} <span className="text-xs text-neutral-500 font-normal">/ {overview.total_assessments}</span>
                </div>
                <div className="text-[11px] text-neutral-500 mt-1">Published examinations</div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800 p-4 rounded-xl">
                <span className="text-xs text-neutral-400 font-medium">Completed Attempts</span>
                <div className="text-2xl font-bold text-emerald-400 mt-1">
                  {overview.completed_attempts}
                </div>
                <div className="text-[11px] text-neutral-500 mt-1">
                  {overview.active_attempts} currently active
                </div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800 p-4 rounded-xl">
                <span className="text-xs text-neutral-400 font-medium">Average Score</span>
                <div className="text-2xl font-bold text-cyan-400 mt-1">
                  {overview.average_score_pct.toFixed(1)}%
                </div>
                <div className="text-[11px] text-neutral-500 mt-1">Across completed tests</div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800 p-4 rounded-xl">
                <span className="text-xs text-neutral-400 font-medium">Pass Rate</span>
                <div className="text-2xl font-bold text-emerald-300 mt-1">
                  {overview.pass_percentage.toFixed(1)}%
                </div>
                <div className="text-[11px] text-neutral-500 mt-1">Meeting pass threshold</div>
              </div>

              <div className="bg-neutral-900/70 border border-neutral-800 p-4 rounded-xl">
                <span className="text-xs text-neutral-400 font-medium">Completion Rate</span>
                <div className="text-2xl font-bold text-purple-400 mt-1">
                  {overview.completion_percentage.toFixed(1)}%
                </div>
                <div className="text-[11px] text-neutral-500 mt-1">Started to submission</div>
              </div>
            </div>
          )}

          {/* Section 2: Assessment Focus & Quick Deep Dive */}
          <div className="bg-gradient-to-r from-neutral-900 to-neutral-950 border border-neutral-800 rounded-2xl p-6 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-bold text-orange-400 uppercase tracking-wider">
                  Assessment Focus
                </span>
                <h3 className="text-lg font-bold text-neutral-100">
                  Assessment-Level Performance Analysis
                </h3>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={selectedAssessmentId}
                  onChange={(e) => setSelectedAssessmentId(e.target.value)}
                  className="bg-neutral-950 border border-neutral-700 text-neutral-200 text-xs rounded-xl px-3 py-2 outline-none focus:border-orange-500"
                >
                  {assessments.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.title} ({a.status})
                    </option>
                  ))}
                </select>

                {activeAssessment && (
                  <>
                    <button
                      onClick={() =>
                        setAnalyticsModalAssessment({
                          id: activeAssessment.id,
                          title: activeAssessment.title,
                        })
                      }
                      className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-semibold transition shadow-sm"
                    >
                      Deep Dive Analytics
                    </button>

                    <button
                      onClick={() =>
                        setProctoringModalAssessment({
                          id: activeAssessment.id,
                          title: activeAssessment.title,
                        })
                      }
                      className="px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-orange-400 border border-orange-500/30 rounded-xl text-xs font-medium transition"
                      title="Proctoring Review Drawer"
                    >
                      🛡️ Proctoring Review
                    </button>

                    <button
                      onClick={handleExportSelectedAssessment}
                      disabled={exportingAssessment}
                      className="px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border border-neutral-700 rounded-xl text-xs font-medium transition"
                      title="Export Results CSV"
                    >
                      {exportingAssessment ? "Exporting..." : "Export CSV"}
                    </button>
                  </>
                )}
              </div>
            </div>

            {activeAssessment && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-neutral-400 pt-2 border-t border-neutral-800/80">
                <div>
                  Duration: <b className="text-neutral-200">{activeAssessment.duration_minutes} mins</b>
                </div>
                <div>
                  Total Marks: <b className="text-neutral-200">{activeAssessment.total_marks} pts</b>
                </div>
                <div>
                  Passing Score: <b className="text-neutral-200">{activeAssessment.passing_marks} pts</b>
                </div>
                <div>
                  Difficulty: <b className="text-orange-400">{activeAssessment.difficulty}</b>
                </div>
              </div>
            )}
          </div>

          {/* Section 3: Cohort Performance & Distributions */}
          {cohort && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Score Distribution Chart */}
              <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
                    <span>📊</span> Cohort Score Distribution
                  </h3>
                  <span className="text-xs text-neutral-500">
                    Cohort Average: <b className="text-cyan-400">{cohort.average_cohort_score_pct.toFixed(1)}%</b>
                  </span>
                </div>

                <div className="space-y-3.5">
                  {cohort.score_distribution.map((bucket) => (
                    <div key={bucket.range_label} className="space-y-1">
                      <div className="flex justify-between text-xs text-neutral-300">
                        <span>{bucket.range_label}</span>
                        <span className="font-semibold text-orange-400">
                          {bucket.count} candidate{bucket.count !== 1 ? "s" : ""} ({bucket.percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="w-full h-3 bg-neutral-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-orange-500 to-amber-400 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(bucket.percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Topic Mastery Proficiencies */}
              <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
                    <span>🧠</span> Topic Mastery Proficiencies
                  </h3>
                  <span className="text-xs text-neutral-500">Aggregated student mastery</span>
                </div>

                {cohort.topic_proficiencies.length === 0 ? (
                  <p className="text-xs text-neutral-500 italic py-12 text-center">
                    No topic mastery records recorded across students.
                  </p>
                ) : (
                  <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                    {cohort.topic_proficiencies.map((t) => (
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
          )}

          {/* Section 4: Systemic Alerts: Frequently Failed Topics */}
          {cohort && cohort.frequently_failed_topics.length > 0 && (
            <div className="p-4 bg-rose-950/20 border border-rose-900/50 rounded-2xl flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-rose-300">
                  Action Required: Frequently Failed Topics (Cohort Average &lt; 50%)
                </h4>
                <p className="text-xs text-neutral-400">
                  The following topics demonstrate widespread student struggle. Consider recommending adaptive review modules or supplemental practice:
                </p>
                <div className="flex flex-wrap gap-2 pt-1">
                  {cohort.frequently_failed_topics.map((top) => (
                    <span key={top} className="px-2.5 py-0.5 bg-rose-900/40 text-rose-300 border border-rose-700/50 rounded-lg text-xs font-semibold">
                      {top}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Section 5: Student Leaderboards & At-Risk Candidates */}
          {cohort && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Top Performers */}
              <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                  <span>🏆</span> Top Performers
                </h3>
                {cohort.top_performers.length === 0 ? (
                  <p className="text-xs text-neutral-500 italic py-6 text-center">
                    No completed assessment attempts recorded.
                  </p>
                ) : (
                  <div className="divide-y divide-neutral-800/60">
                    {cohort.top_performers.map((p, idx) => (
                      <div key={p.candidate_id} className="py-2.5 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-3">
                          <span className="w-5 h-5 rounded-full bg-neutral-800 text-neutral-300 flex items-center justify-center font-bold text-[10px]">
                            {idx + 1}
                          </span>
                          <div>
                            <div className="font-semibold text-neutral-200">{p.full_name}</div>
                            <div className="text-[10px] text-neutral-500">{p.email}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-emerald-400">{p.score_pct?.toFixed(1)}%</span>
                          <button
                            onClick={() => setAuditCandidateId(p.candidate_id)}
                            className="px-2 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-[10px] transition"
                          >
                            Audit
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* At-Risk Candidates */}
              <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                  <span>⚠️</span> At-Risk Candidates (Average Score &lt; 40%)
                </h3>
                {cohort.at_risk_candidates.length === 0 ? (
                  <p className="text-xs text-neutral-500 italic py-6 text-center">
                    No students currently flagged as at-risk.
                  </p>
                ) : (
                  <div className="divide-y divide-neutral-800/60">
                    {cohort.at_risk_candidates.map((c) => (
                      <div key={c.candidate_id} className="py-2.5 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-semibold text-neutral-200">{c.full_name}</div>
                          <div className="text-[10px] text-neutral-500">{c.email}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-rose-400">{c.score_pct?.toFixed(1)}%</span>
                          <button
                            onClick={() => setAuditCandidateId(c.candidate_id)}
                            className="px-2 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-[10px] transition"
                          >
                            Audit
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Assessment Analytics Modal */}
      {analyticsModalAssessment && (
        <AssessmentAnalyticsModal
          assessmentId={analyticsModalAssessment.id}
          assessmentTitle={analyticsModalAssessment.title}
          isOpen={true}
          onClose={() => setAnalyticsModalAssessment(null)}
          onOpenCandidateReport={(cId) => setAuditCandidateId(cId)}
          onOpenProctoringReview={(assId, assTitle) => {
            setAnalyticsModalAssessment(null);
            setProctoringModalAssessment({ id: assId, title: assTitle });
          }}
        />
      )}

      {/* Proctoring Review Modal */}
      {proctoringModalAssessment && (
        <InstructorProctoringModal
          assessmentId={proctoringModalAssessment.id}
          assessmentTitle={proctoringModalAssessment.title}
          isOpen={true}
          onClose={() => setProctoringModalAssessment(null)}
        />
      )}

      {/* Candidate Performance Audit Modal */}
      {auditCandidateId && (
        <CandidatePerformanceModal
          candidateId={auditCandidateId}
          isOpen={true}
          onClose={() => setAuditCandidateId(null)}
        />
      )}
    </div>
  );
}
