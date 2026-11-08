"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  createAssessmentApi,
  getAssessmentCohortResultsApi,
  listAssessmentsApi,
  listQuestionsApi,
  publishAssessmentApi,
} from "@/lib/api/assessment";
import {
  AssessmentAdmin,
  AssessmentCreatePayload,
  CohortAttemptResult,
  QuestionAdmin,
} from "@/types/assessment";
import { InstructorProctoringModal } from "@/components/proctoring/InstructorProctoringModal";
import { AssessmentAnalyticsModal } from "@/components/analytics/AssessmentAnalyticsModal";

function cleanDisplayName(name: string): string {
  return name.replace(/^(Stage\s*\d+\s*|Sprint\s*\d+\s*)/i, "").trim() || name;
}

export function AssessmentManagementSection() {
  const [assessments, setAssessments] = useState<AssessmentAdmin[]>([]);
  const [questions, setQuestions] = useState<QuestionAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [selectedQuestions, setSelectedQuestions] = useState<string[]>([]);
  const [formData, setFormData] = useState<AssessmentCreatePayload>({
    title: "",
    description: "",
    instructions: "Write clean, modular code. Handle all corner cases and large array sizes.",
    duration_minutes: 60,
    total_marks: 100,
    passing_marks: 40,
    difficulty: "MEDIUM",
    allowed_languages: "ALL_ACTIVE",
  });

  // Results Modal
  const [resultsModalOpen, setResultsModalOpen] = useState(false);
  const [cohortResults, setCohortResults] = useState<CohortAttemptResult[]>([]);
  const [selectedAssessmentTitle, setSelectedAssessmentTitle] = useState("");
  const [resultsLoading, setResultsLoading] = useState(false);

  // Proctoring Modal
  const [proctoringModalOpen, setProctoringModalOpen] = useState(false);
  const [selectedProctoringAssessment, setSelectedProctoringAssessment] = useState<AssessmentAdmin | null>(null);

  // Analytics Modal
  const [analyticsModalOpen, setAnalyticsModalOpen] = useState(false);
  const [selectedAnalyticsAssessment, setSelectedAnalyticsAssessment] = useState<AssessmentAdmin | null>(null);

  // Proctoring Form Config
  const [proctoringSettings, setProctoringSettings] = useState({
    enable_tab_monitoring: true,
    require_fullscreen: true,
    enable_webcam: false,
  });

  const fetchAssessmentsAndQuestions = useCallback(async () => {
    const [assRes, qRes] = await Promise.all([
      listAssessmentsApi(),
      listQuestionsApi({ is_archived: false }),
    ]);

    if (assRes.success && assRes.data) {
      setAssessments(assRes.data);
    } else {
      setError(assRes.error?.message || "Failed to load assessments.");
    }

    if (qRes.success && qRes.data) {
      setQuestions(qRes.data);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await fetchAssessmentsAndQuestions();
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [fetchAssessmentsAndQuestions]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    const payload: AssessmentCreatePayload = {
      ...formData,
      question_ids: selectedQuestions,
      proctoring_config: {
        enable_tab_monitoring: proctoringSettings.enable_tab_monitoring,
        require_fullscreen: proctoringSettings.require_fullscreen,
        enable_webcam: proctoringSettings.enable_webcam,
        enable_focus_monitoring: true,
        max_tab_switches_warning: 2,
        max_tab_switches_alert: 4,
        max_blur_seconds_alert: 60,
        max_fullscreen_exits_alert: 3,
      },
    };

    const res = await createAssessmentApi(payload);
    if (res.success) {
      setShowCreateModal(false);
      setSelectedQuestions([]);
      await fetchAssessmentsAndQuestions();
    } else {
      setFormError(res.error?.message || "Failed to create assessment.");
    }
    setFormSubmitting(false);
  };

  const handleViewProctoring = (assessment: AssessmentAdmin) => {
    setSelectedProctoringAssessment(assessment);
    setProctoringModalOpen(true);
  };

  const handlePublish = async (assessmentId: string) => {
    if (!confirm("Are you sure you want to publish this assessment? Candidates will be able to begin their examination.")) {
      return;
    }
    const res = await publishAssessmentApi(assessmentId);
    if (res.success) {
      await fetchAssessmentsAndQuestions();
    } else {
      alert(res.error?.message || "Failed to publish assessment.");
    }
  };

  const handleViewResults = async (assessment: AssessmentAdmin) => {
    setSelectedAssessmentTitle(assessment.title);
    setResultsModalOpen(true);
    setResultsLoading(true);

    const res = await getAssessmentCohortResultsApi(assessment.id);
    if (res.success && res.data) {
      setCohortResults(res.data.results);
    } else {
      alert(res.error?.message || "Failed to load examination cohort results.");
    }
    setResultsLoading(false);
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
            Assessment Orchestration
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Create timed examinations, configure pass/fail thresholds, attach problem sets, and review cohort performance.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-white bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 rounded-xl shadow-sm hover:shadow transition-all duration-150"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
          </svg>
          Create Assessment
        </button>
      </div>

      {loading ? (
        <div className="py-16 text-center text-sm text-slate-500 space-y-3">
          <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p>Loading assessment registry...</p>
        </div>
      ) : error ? (
        <div className="py-4 text-center text-sm text-rose-500 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl">{error}</div>
      ) : assessments.length === 0 ? (
        <div className="py-16 text-center text-sm text-slate-500 max-w-md mx-auto space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="font-semibold text-slate-700 dark:text-slate-300">No Assessments Configured</p>
          <p className="text-xs text-slate-400">Click &quot;Create Assessment&quot; to configure your first examination session.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {assessments.map((a) => (
            <div
              key={a.id}
              className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-800/30 hover:border-orange-500/30 hover:shadow-md transition-all duration-200 flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-base text-slate-900 dark:text-white leading-snug">{a.title}</h3>
                    <p className="text-xs text-slate-500 line-clamp-2 mt-1 leading-relaxed">{a.description || "No description provided."}</p>
                  </div>
                  <span
                    className={`shrink-0 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                      a.status === "PUBLISHED"
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                        : a.status === "DRAFT"
                        ? "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                        : "bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                    }`}
                  >
                    {a.status}
                  </span>
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <div className="grid grid-cols-3 gap-2 text-center py-2.5 px-3 rounded-xl bg-slate-100/60 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-800 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block tracking-wider">Duration</span>
                    <span className="font-bold text-slate-800 dark:text-slate-200">{a.duration_minutes}m</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block tracking-wider">Pass / Total</span>
                    <span className="font-bold text-slate-800 dark:text-slate-200">
                      {a.passing_marks} / {a.total_marks}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block tracking-wider">Problems</span>
                    <span className="font-bold text-slate-800 dark:text-slate-200">{a.questions.length}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-slate-500 font-medium">
                    Languages: <strong className="text-slate-700 dark:text-slate-300">{a.allowed_languages}</strong>
                  </span>
                  <div className="flex items-center gap-2">
                    {a.status === "DRAFT" && (
                      <button
                        onClick={() => handlePublish(a.id)}
                        className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition shadow-sm"
                      >
                        Publish
                      </button>
                    )}
                    <button
                      onClick={() => handleViewResults(a)}
                      className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold text-xs rounded-xl border border-slate-200 dark:border-slate-700 transition"
                    >
                      Cohort Results
                    </button>
                    <button
                      onClick={() => handleViewProctoring(a)}
                      className="px-3.5 py-1.5 bg-orange-50 hover:bg-orange-100 dark:bg-orange-950/40 dark:hover:bg-orange-900/40 text-orange-700 dark:text-orange-300 font-semibold text-xs rounded-xl border border-orange-200 dark:border-orange-800 transition flex items-center gap-1.5"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                      <span>Proctoring</span>
                    </button>
                    <button
                      onClick={() => {
                        setSelectedAnalyticsAssessment(a);
                        setAnalyticsModalOpen(true);
                      }}
                      className="px-3.5 py-1.5 bg-cyan-50 hover:bg-cyan-100 dark:bg-cyan-950/40 dark:hover:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300 font-semibold text-xs rounded-xl border border-cyan-200 dark:border-cyan-800 transition flex items-center gap-1.5"
                    >
                      <span>📊</span>
                      <span>Analytics</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Assessment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-7 space-y-5">
            <div className="flex justify-between items-center border-b border-slate-200 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">Configure Assessment</h3>
                <p className="text-xs text-slate-400 mt-0.5">Set assessment limits, scoring thresholds, and attach questions.</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                &times;
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-xl text-xs font-semibold">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Assessment Title *
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. SDE Coding Assessment - 2026 Cohort"
                  className="w-full bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-xs font-medium focus:outline-none focus:border-orange-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  value={formData.description || ""}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Candidate briefing notes..."
                  className="w-full bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-xs font-medium focus:outline-none focus:border-orange-500 leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Duration (Mins) *
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={1440}
                    required
                    value={formData.duration_minutes}
                    onChange={(e) => setFormData({ ...formData, duration_minutes: Number(e.target.value) })}
                    className="w-full bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-xs font-medium focus:outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Total Marks *
                  </label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={formData.total_marks}
                    onChange={(e) => setFormData({ ...formData, total_marks: Number(e.target.value) })}
                    className="w-full bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-xs font-medium focus:outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Passing Marks *
                  </label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={formData.passing_marks}
                    onChange={(e) => setFormData({ ...formData, passing_marks: Number(e.target.value) })}
                    className="w-full bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-xs font-medium focus:outline-none focus:border-orange-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Allowed Languages
                </label>
                <select
                  value={formData.allowed_languages}
                  onChange={(e) => setFormData({ ...formData, allowed_languages: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white text-xs font-semibold focus:outline-none focus:border-orange-500"
                >
                  <option value="ALL_ACTIVE">All Active (Python 3, Java)</option>
                  <option value="Python 3">Python 3 Only</option>
                  <option value="Java">Java Only</option>
                  <option value="Python 3,Java">Python 3 and Java</option>
                </select>
              </div>

              {/* Select Questions */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Attach Questions from Repository ({selectedQuestions.length} selected)
                </label>
                {questions.length === 0 ? (
                  <p className="text-xs text-slate-500 py-2">No questions available in question bank.</p>
                ) : (
                  <div className="max-h-40 overflow-y-auto border border-slate-300 dark:border-slate-700 rounded-xl p-2.5 space-y-1.5 bg-slate-50/50 dark:bg-slate-800/30">
                    {questions.map((q) => {
                      const isChecked = selectedQuestions.includes(q.id);
                      return (
                        <label
                          key={q.id}
                          className="flex items-center gap-2.5 text-xs p-2 hover:bg-white dark:hover:bg-slate-800 rounded-lg cursor-pointer transition border border-transparent hover:border-slate-200 dark:hover:border-slate-700"
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedQuestions([...selectedQuestions, q.id]);
                              } else {
                                setSelectedQuestions(selectedQuestions.filter((id) => id !== q.id));
                              }
                            }}
                            className="rounded border-slate-300 text-orange-600 focus:ring-orange-500"
                          />
                          <span className="font-semibold text-slate-800 dark:text-slate-200">{q.title}</span>
                          <span className="text-[11px] text-slate-400">({q.difficulty} • {q.marks} pts)</span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Proctoring & Integrity Configuration */}
              <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Assessment Integrity & Proctoring Settings
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <label className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={proctoringSettings.enable_tab_monitoring}
                      onChange={(e) =>
                        setProctoringSettings({
                          ...proctoringSettings,
                          enable_tab_monitoring: e.target.checked,
                        })
                      }
                      className="rounded border-slate-300 text-orange-600 focus:ring-orange-500"
                    />
                    <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                      Tab & Focus Monitoring
                    </span>
                  </label>

                  <label className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={proctoringSettings.require_fullscreen}
                      onChange={(e) =>
                        setProctoringSettings({
                          ...proctoringSettings,
                          require_fullscreen: e.target.checked,
                        })
                      }
                      className="rounded border-slate-300 text-orange-600 focus:ring-orange-500"
                    />
                    <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                      Require Fullscreen
                    </span>
                  </label>

                  <label className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={proctoringSettings.enable_webcam}
                      onChange={(e) =>
                        setProctoringSettings({
                          ...proctoringSettings,
                          enable_webcam: e.target.checked,
                        })
                      }
                      className="rounded border-slate-300 text-orange-600 focus:ring-orange-500"
                    />
                    <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                      Webcam Presence
                    </span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-5 py-2 bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white text-xs font-bold uppercase tracking-wider rounded-xl transition shadow disabled:opacity-50"
                >
                  {formSubmitting ? "Creating..." : "Save Assessment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cohort Results Modal */}
      {resultsModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6 sm:p-7 space-y-5">
            <div className="flex justify-between items-center border-b border-slate-200 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">Cohort Submission Results</h3>
                <p className="text-xs text-slate-400 mt-0.5">{selectedAssessmentTitle}</p>
              </div>
              <button
                onClick={() => setResultsModalOpen(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                &times;
              </button>
            </div>

            {resultsLoading ? (
              <div className="py-16 text-center text-sm text-slate-500 space-y-3">
                <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p>Loading candidate submissions...</p>
              </div>
            ) : cohortResults.length === 0 ? (
              <div className="py-12 text-center text-sm text-slate-500 max-w-md mx-auto space-y-2">
                <p className="font-semibold text-slate-700 dark:text-slate-300">No Attempts Recorded</p>
                <p className="text-xs text-slate-400">No candidates have started or completed this examination yet.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                  <thead className="bg-slate-50/80 dark:bg-slate-800/60 text-xs font-semibold text-slate-700 dark:text-slate-200 uppercase tracking-wider border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="px-4 py-3">Candidate</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Score</th>
                      <th className="px-4 py-3">Percentage</th>
                      <th className="px-4 py-3">Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {cohortResults.map((r) => {
                      const cleanName = cleanDisplayName(r.candidate_name);
                      const initial = cleanName.charAt(0).toUpperCase();

                      return (
                        <tr key={r.attempt_id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2.5">
                              <div className="w-7 h-7 rounded-full bg-orange-100 dark:bg-orange-950/60 text-orange-700 dark:text-orange-300 flex items-center justify-center font-bold text-xs border border-orange-200 dark:border-orange-800">
                                {initial}
                              </div>
                              <div>
                                <div className="font-semibold text-slate-900 dark:text-white text-xs">{cleanName}</div>
                                <div className="text-[11px] text-slate-400">{r.candidate_email}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                              {r.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-bold text-slate-900 dark:text-white text-xs">{r.total_score} pts</td>
                          <td className="px-4 py-3 text-xs font-medium text-slate-700 dark:text-slate-300">{r.percentage}%</td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                                r.is_passed
                                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                                  : "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
                              }`}
                            >
                              {r.is_passed ? "PASSED" : "FAILED"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Instructor Proctoring Audit Modal */}
      {selectedProctoringAssessment && (
        <InstructorProctoringModal
          assessmentId={selectedProctoringAssessment.id}
          assessmentTitle={selectedProctoringAssessment.title}
          isOpen={proctoringModalOpen}
          onClose={() => {
            setProctoringModalOpen(false);
            setSelectedProctoringAssessment(null);
          }}
        />
      )}

      {/* Assessment Analytics Modal */}
      {selectedAnalyticsAssessment && (
        <AssessmentAnalyticsModal
          assessmentId={selectedAnalyticsAssessment.id}
          assessmentTitle={selectedAnalyticsAssessment.title}
          isOpen={analyticsModalOpen}
          onClose={() => {
            setAnalyticsModalOpen(false);
            setSelectedAnalyticsAssessment(null);
          }}
          onOpenProctoringReview={() => {
            setAnalyticsModalOpen(false);
            setSelectedProctoringAssessment(selectedAnalyticsAssessment);
            setProctoringModalOpen(true);
          }}
        />
      )}
    </div>
  );
}
