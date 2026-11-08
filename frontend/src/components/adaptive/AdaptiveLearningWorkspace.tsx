"use client";

import React, { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import {
  getMasteryHistoryApi,
  getPracticeQuestionApi,
  getQuestionRecommendationsApi,
  getStrengthsWeaknessesApi,
  getStudentPerformanceApi,
  getTopicMasteryApi,
  getTopicPracticeDetailApi,
  getTopicsCatalogApi,
  runPracticeSampleApi,
  submitPracticeSolutionApi,
} from "@/lib/api/adaptive";
import { listStudentLanguagesApi } from "@/lib/api/assessment";
import {
  MasteryHistorySnapshot,
  QuestionRecommendationItem,
  StrengthsAndWeaknessesResponse,
  StudentPerformanceResponse,
  TopicCatalogItem,
  TopicMasteryItem,
  TopicMasteryListResponse,
  TopicPracticeDetailResponse,
  TopicPracticeQuestionItem,
} from "@/types/adaptive";
import { ProgrammingLanguageInfo, QuestionPublic, SubmissionResponse } from "@/types/assessment";

// Dynamic Monaco Editor import for Next.js SSR compatibility
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const BOILERPLATE_PYTHON = `import sys

def solve():
    # Read standard input and print output
    lines = sys.stdin.read().split()
    if not lines:
        return
    # Your practice logic here
    print(" ".join(lines))

if __name__ == "__main__":
    solve()
`;

const BOILERPLATE_JAVA = `import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        // Your practice logic here
        while (scanner.hasNext()) {
            System.out.println(scanner.next());
        }
    }
}
`;

export function AdaptiveLearningWorkspace() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Core Adaptive States
  const [masteryData, setMasteryData] = useState<TopicMasteryListResponse | null>(null);
  const [performanceData, setPerformanceData] = useState<StudentPerformanceResponse | null>(null);
  const [swData, setSwData] = useState<StrengthsAndWeaknessesResponse | null>(null);
  const [recommendations, setRecommendations] = useState<QuestionRecommendationItem[]>([]);
  const [historySnapshots, setHistorySnapshots] = useState<MasteryHistorySnapshot[]>([]);
  const [languages, setLanguages] = useState<ProgrammingLanguageInfo[]>([]);

  // Filter/Sort State
  const [activeFilterTab, setActiveFilterTab] = useState<"all" | "strong" | "weak" | "unattempted">("all");

  // Practice Modal State
  const [practiceModalOpen, setPracticeModalOpen] = useState(false);
  const [activePracticeQuestion, setActivePracticeQuestion] = useState<QuestionPublic | null>(null);
  const [practiceLanguage, setPracticeLanguage] = useState<ProgrammingLanguageInfo | null>(null);
  const [practiceCode, setPracticeCode] = useState<string>("");
  const [practiceExecuting, setPracticeExecuting] = useState(false);
  const [practiceResult, setPracticeResult] = useState<SubmissionResponse | null>(null);
  const [practiceOutputTab, setPracticeOutputTab] = useState<"tests" | "static" | "ai">("tests");

  // Topic Practice Navigation State
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [topicDetail, setTopicDetail] = useState<TopicPracticeDetailResponse | null>(null);
  const [loadingTopic, setLoadingTopic] = useState<boolean>(false);
  const [topicDifficultyFilter, setTopicDifficultyFilter] = useState<"ALL" | "EASY" | "MEDIUM" | "HARD">("ALL");
  const [topicStatusFilter, setTopicStatusFilter] = useState<"ALL" | "SOLVED" | "UNSOLVED">("ALL");

  const handleSelectTopic = async (topicName: string) => {
    setSelectedTopic(topicName);
    setLoadingTopic(true);
    setTopicDifficultyFilter("ALL");
    setTopicStatusFilter("ALL");
    const res = await getTopicPracticeDetailApi(topicName);
    if (res.success && res.data) {
      setTopicDetail(res.data);
    } else {
      alert(res.error?.message || `Failed to load practice questions for ${topicName}.`);
    }
    setLoadingTopic(false);
  };

  const handleBackToDashboard = async () => {
    setSelectedTopic(null);
    setTopicDetail(null);
    await loadAdaptiveData();
  };

  const handleRefreshTopicDetail = async (topicName: string) => {
    const res = await getTopicPracticeDetailApi(topicName);
    if (res.success && res.data) {
      setTopicDetail(res.data);
    }
  };


  const loadAdaptiveData = useCallback(async () => {
    setLoading(true);
    setError(null);

    const [perfRes, masteryRes, swRes, recsRes, histRes, langRes] = await Promise.all([
      getStudentPerformanceApi(),
      getTopicMasteryApi(),
      getStrengthsWeaknessesApi(),
      getQuestionRecommendationsApi(6),
      getMasteryHistoryApi(undefined, 20),
      listStudentLanguagesApi(),
    ]);

    if (perfRes.success && perfRes.data) setPerformanceData(perfRes.data);
    if (masteryRes.success && masteryRes.data) setMasteryData(masteryRes.data);
    if (swRes.success && swRes.data) setSwData(swRes.data);
    if (recsRes.success && recsRes.data) setRecommendations(recsRes.data.recommendations);
    if (histRes.success && histRes.data) setHistorySnapshots(histRes.data.history);
    if (langRes.success && langRes.data) {
      setLanguages(langRes.data);
      if (langRes.data.length > 0 && !practiceLanguage) {
        setPracticeLanguage(langRes.data[0]);
      }
    }

    if (!perfRes.success && !masteryRes.success) {
      setError(perfRes.error?.message || "Failed to load adaptive performance profile.");
    }
    setLoading(false);
  }, [practiceLanguage]);

  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await loadAdaptiveData();
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [loadAdaptiveData]);

  // Practice Modal Trigger
  const handleStartPractice = async (questionId: string) => {
    setPracticeResult(null);
    setPracticeModalOpen(true);

    const res = await getPracticeQuestionApi(questionId);
    if (res.success && res.data) {
      setActivePracticeQuestion(res.data);
      const isJava = practiceLanguage?.name.toLowerCase().includes("java");
      setPracticeCode(isJava ? BOILERPLATE_JAVA : BOILERPLATE_PYTHON);
    } else {
      alert(res.error?.message || "Failed to load practice challenge.");
      setPracticeModalOpen(false);
    }
  };

  const handlePracticeLanguageChange = (langId: string) => {
    const lang = languages.find((l) => l.id === langId);
    if (!lang) return;
    setPracticeLanguage(lang);

    const isJava = lang.name.toLowerCase().includes("java");
    if (practiceCode === BOILERPLATE_PYTHON && isJava) {
      setPracticeCode(BOILERPLATE_JAVA);
    } else if (practiceCode === BOILERPLATE_JAVA && !isJava) {
      setPracticeCode(BOILERPLATE_PYTHON);
    }
  };

  const handleRunPracticeSample = async () => {
    if (!activePracticeQuestion || !practiceLanguage) return;
    setPracticeExecuting(true);
    setPracticeResult(null);

    const res = await runPracticeSampleApi(activePracticeQuestion.id, {
      programming_language_id: practiceLanguage.id,
      source_code: practiceCode,
    });

    if (res.success && res.data) {
      setPracticeResult(res.data);
    } else {
      alert(res.error?.message || "Sample test execution failed.");
    }
    setPracticeExecuting(false);
  };

  const handleSubmitPractice = async () => {
    if (!activePracticeQuestion || !practiceLanguage) return;
    setPracticeExecuting(true);
    setPracticeResult(null);

    const res = await submitPracticeSolutionApi(activePracticeQuestion.id, {
      programming_language_id: practiceLanguage.id,
      source_code: practiceCode,
    });

    if (res.success && res.data) {
      setPracticeResult(res.data);
      // Reload adaptive metrics in background to reflect real-time impact!
      await loadAdaptiveData();
      if (selectedTopic) {
        await handleRefreshTopicDetail(selectedTopic);
      }
    } else {
      alert(res.error?.message || "Practice evaluation failed.");
    }
    setPracticeExecuting(false);
  };

  // Filter topics for view
  const filteredTopics = (masteryData?.topics || []).filter((t) => {
    if (activeFilterTab === "strong") return t.mastery_score >= 65.0 || t.success_rate >= 75.0;
    if (activeFilterTab === "weak") return t.questions_attempted > 0 && (t.mastery_score < 50.0 || t.success_rate < 50.0);
    if (activeFilterTab === "unattempted") return t.questions_attempted === 0;
    return true;
  });

  if (loading && !masteryData) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-12 text-center space-y-4">
        <div className="w-8 h-8 border-3 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Calculating topic mastery and generating adaptive recommendations...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {selectedTopic ? (
        /* --------------------------------------------------------------------- */
        /* DEDICATED TOPIC PRACTICE VIEW                                         */
        /* --------------------------------------------------------------------- */
        <div className="space-y-6">
          {/* Breadcrumb Navigation & Back Button */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <button
              onClick={handleBackToDashboard}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-bold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition shadow-sm cursor-pointer"
            >
              <span>←</span>
              <span>Back to Mastery Dashboard</span>
            </button>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Adaptive Practice &gt; <span className="font-bold text-slate-800 dark:text-slate-200">{selectedTopic}</span>
            </div>
          </div>

          {loadingTopic || !topicDetail ? (
            <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-16 text-center space-y-3">
              <div className="w-8 h-8 border-3 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Loading practice curriculum for {selectedTopic}...
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Topic Hero Card */}
              <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 text-white rounded-3xl border border-slate-800 p-6 sm:p-8 shadow-xl space-y-5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1.5 max-w-2xl">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-orange-500/20 text-orange-300 border border-orange-500/30">
                      Curated Topic Curriculum
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                      {topicDetail.topic} Practice
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                      {topicDetail.description}
                    </p>
                  </div>

                  {/* Topic Mastery Summary Badges */}
                  <div className="flex flex-wrap gap-2.5 items-center">
                    <div className="p-3 rounded-2xl bg-slate-800/80 border border-slate-700 text-center min-w-[110px]">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Mastery</span>
                      <div className="text-xl font-extrabold text-orange-400 mt-0.5">
                        {topicDetail.mastery_score}%
                      </div>
                      <span className="text-[10px] font-semibold text-slate-300">{topicDetail.mastery_level}</span>
                    </div>
                    <div className="p-3 rounded-2xl bg-slate-800/80 border border-slate-700 text-center min-w-[110px]">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Solved</span>
                      <div className="text-xl font-extrabold text-emerald-400 mt-0.5">
                        {topicDetail.questions_solved} / {topicDetail.total_questions}
                      </div>
                      <span className="text-[10px] font-semibold text-slate-300">
                        {topicDetail.total_questions > 0
                          ? `${Math.round((topicDetail.questions_solved / topicDetail.total_questions) * 100)}% Complete`
                          : "0%"}
                      </span>
                    </div>
                    <div className="p-3 rounded-2xl bg-slate-800/80 border border-slate-700 text-center min-w-[120px]">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Target Level</span>
                      <div className="text-sm font-extrabold text-amber-300 mt-1 uppercase">
                        {topicDetail.recommended_difficulty}
                      </div>
                      <span className="text-[10px] font-semibold text-slate-400">Confidence: {topicDetail.confidence_level}</span>
                    </div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1 pt-1">
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-2 rounded-full bg-gradient-to-r from-orange-500 to-amber-500 transition-all duration-300"
                      style={{
                        width: `${
                          topicDetail.total_questions > 0
                            ? Math.max(5, (topicDetail.questions_solved / topicDetail.total_questions) * 100)
                            : 0
                        }%`,
                      }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Recommended Next Challenge Card */}
              {topicDetail.recommended_question && (
                <div className="p-5 sm:p-6 rounded-3xl border border-orange-200 dark:border-orange-800/80 bg-gradient-to-br from-orange-50/70 via-white to-amber-50/40 dark:from-orange-950/20 dark:via-slate-900 dark:to-amber-950/10 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-orange-500 text-white shadow-sm">
                        Recommended Next Challenge
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          topicDetail.recommended_question.difficulty === "EASY"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                            : topicDetail.recommended_question.difficulty === "HARD"
                            ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                            : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                        }`}
                      >
                        {topicDetail.recommended_question.difficulty}
                      </span>
                      <span className="text-xs text-slate-500">{topicDetail.recommended_question.marks} pts</span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      {topicDetail.recommended_question.title}
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-slate-400">
                      Calibrated for your current {topicDetail.mastery_level.toLowerCase()} mastery tier ({topicDetail.mastery_score}%).
                    </p>
                  </div>
                  <button
                    onClick={() => handleStartPractice(topicDetail.recommended_question!.id)}
                    className="px-5 py-2.5 text-xs font-bold text-white bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 rounded-xl shadow-md transition shrink-0 cursor-pointer"
                  >
                    Start Practice →
                  </button>
                </div>
              )}

              {/* Question Browser Section */}
              <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                      Topic Question Bank
                    </h2>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                      Select any question to open the interactive coding workspace, run sample tests, and submit for evaluation.
                    </p>
                  </div>

                  {/* Filters Toolbar */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Difficulty Filter */}
                    <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl text-xs">
                      <button
                        onClick={() => setTopicDifficultyFilter("ALL")}
                        className={`px-2.5 py-1 font-bold rounded-lg transition cursor-pointer ${
                          topicDifficultyFilter === "ALL"
                            ? "bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white"
                            : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        }`}
                      >
                        All
                      </button>
                      <button
                        onClick={() => setTopicDifficultyFilter("EASY")}
                        className={`px-2.5 py-1 font-bold rounded-lg transition cursor-pointer ${
                          topicDifficultyFilter === "EASY"
                            ? "bg-white dark:bg-slate-900 shadow-sm text-emerald-700 dark:text-emerald-400"
                            : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        }`}
                      >
                        Easy
                      </button>
                      <button
                        onClick={() => setTopicDifficultyFilter("MEDIUM")}
                        className={`px-2.5 py-1 font-bold rounded-lg transition cursor-pointer ${
                          topicDifficultyFilter === "MEDIUM"
                            ? "bg-white dark:bg-slate-900 shadow-sm text-amber-700 dark:text-amber-400"
                            : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        }`}
                      >
                        Medium
                      </button>
                      <button
                        onClick={() => setTopicDifficultyFilter("HARD")}
                        className={`px-2.5 py-1 font-bold rounded-lg transition cursor-pointer ${
                          topicDifficultyFilter === "HARD"
                            ? "bg-white dark:bg-slate-900 shadow-sm text-rose-700 dark:text-rose-400"
                            : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        }`}
                      >
                        Hard
                      </button>
                    </div>

                    {/* Status Filter */}
                    <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl text-xs">
                      <button
                        onClick={() => setTopicStatusFilter("ALL")}
                        className={`px-2.5 py-1 font-bold rounded-lg transition cursor-pointer ${
                          topicStatusFilter === "ALL"
                            ? "bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white"
                            : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        }`}
                      >
                        All Status
                      </button>
                      <button
                        onClick={() => setTopicStatusFilter("SOLVED")}
                        className={`px-2.5 py-1 font-bold rounded-lg transition cursor-pointer ${
                          topicStatusFilter === "SOLVED"
                            ? "bg-white dark:bg-slate-900 shadow-sm text-emerald-700 dark:text-emerald-400"
                            : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        }`}
                      >
                        Solved
                      </button>
                      <button
                        onClick={() => setTopicStatusFilter("UNSOLVED")}
                        className={`px-2.5 py-1 font-bold rounded-lg transition cursor-pointer ${
                          topicStatusFilter === "UNSOLVED"
                            ? "bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white"
                            : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        }`}
                      >
                        Unsolved
                      </button>
                    </div>
                  </div>
                </div>

                {/* Questions List */}
                {(() => {
                  const filteredQuestions = topicDetail.questions.filter((q) => {
                    if (topicDifficultyFilter !== "ALL" && q.difficulty.toUpperCase() !== topicDifficultyFilter) {
                      return false;
                    }
                    if (topicStatusFilter === "SOLVED" && !q.is_solved) return false;
                    if (topicStatusFilter === "UNSOLVED" && q.is_solved) return false;
                    return true;
                  });

                  if (filteredQuestions.length === 0) {
                    return (
                      <div className="py-12 text-center text-sm text-slate-500">
                        No questions match the selected difficulty and status filters.
                      </div>
                    );
                  }

                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {filteredQuestions.map((q) => (
                        <div
                          key={q.id}
                          className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 hover:border-orange-500/40 hover:shadow-md transition-all duration-200 flex flex-col justify-between space-y-4"
                        >
                          <div className="space-y-2.5">
                            <div className="flex items-start justify-between gap-2">
                              <span
                                className={`px-2.5 py-0.5 rounded-full text-[11px] font-extrabold uppercase tracking-wider ${
                                  q.difficulty === "EASY"
                                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                                    : q.difficulty === "HARD"
                                    ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
                                    : "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                                }`}
                              >
                                {q.difficulty}
                              </span>

                              {q.is_solved ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                                  <span>✓</span>
                                  <span>Solved</span>
                                </span>
                              ) : q.attempts_count > 0 ? (
                                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                                  Attempted ({q.attempts_count})
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-500">
                                  Unattempted
                                </span>
                              )}
                            </div>

                            <h3 className="font-bold text-sm text-slate-900 dark:text-white leading-snug">
                              {q.title}
                            </h3>

                            <p className="text-xs text-slate-400">
                              {q.marks} marks • {q.time_limit_seconds}s limit • {q.sample_test_case_count} sample {q.sample_test_case_count === 1 ? "case" : "cases"}
                            </p>
                          </div>

                          <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800 flex items-center justify-between">
                            <span className="text-[11px] text-slate-400 font-medium">
                              {q.is_solved ? "Score achieved: 100%" : `${q.attempts_count} submission(s)`}
                            </span>
                            <button
                              onClick={() => handleStartPractice(q.id)}
                              className={`px-3.5 py-1.5 text-xs font-bold rounded-xl shadow-sm transition cursor-pointer ${
                                q.is_solved
                                  ? "bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                                  : "text-white bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700"
                              }`}
                            >
                              {q.is_solved ? "Practice Again →" : "Start Practice →"}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* --------------------------------------------------------------------- */
        /* STANDARD ADAPTIVE DASHBOARD VIEW                                      */
        /* --------------------------------------------------------------------- */
        <>
          {/* --------------------------------------------------------------------- */}
          {/* SECTION 1: HEADER & OVERALL TELEMETRY HERO                            */}
          {/* --------------------------------------------------------------------- */}
          <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 text-white rounded-3xl border border-slate-800 p-6 sm:p-8 shadow-xl relative overflow-hidden">
            <div className="absolute right-0 top-0 -mr-16 -mt-16 w-64 h-64 bg-orange-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
              <div className="space-y-2 max-w-2xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-orange-500/20 text-orange-300 border border-orange-500/30">
                  <span className="w-2 h-2 rounded-full bg-orange-400 animate-pulse"></span>
                  Adaptive Learning Profile Active
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                  Adaptive Mastery &amp; Performance Engine
                </h1>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  Real-time skill telemetry calculated from authoritative code evaluation. Dynamically calibrates difficulty levels and curates practice questions based on verified topic mastery.
                </p>
              </div>

              {/* Quick Status Badges */}
              <div className="flex flex-wrap sm:flex-nowrap gap-3 items-center">
                <div className="p-3.5 rounded-2xl bg-slate-800/80 border border-slate-700 text-center min-w-[130px]">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Overall Mastery</span>
                  <div className="text-2xl font-extrabold text-orange-400 mt-0.5">
                    {masteryData?.overall_mastery_score || 0}%
                  </div>
                  <span className="text-[10px] font-semibold text-slate-300">
                    {masteryData?.overall_mastery_level || "BEGINNER"}
                  </span>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-800/80 border border-slate-700 text-center min-w-[130px]">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Recommended Tier</span>
                  <div className="text-2xl font-extrabold text-emerald-400 mt-0.5">
                    {masteryData?.overall_recommended_difficulty || "EASY"}
                  </div>
                  <span className="text-[10px] font-semibold text-slate-300">Dynamic Calibrated</span>
                </div>
              </div>
            </div>

            {/* 4-Column KPI Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-6 mt-6 border-t border-slate-800 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Questions Solved</span>
                <span className="text-lg font-bold text-white">
                  {performanceData?.total_questions_solved || 0}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Questions Attempted</span>
                <span className="text-lg font-bold text-white">
                  {performanceData?.total_questions_attempted || 0}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Submission Accuracy</span>
                <span className="text-lg font-bold text-emerald-400">
                  {performanceData?.overall_success_rate || 0}%
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Completed Examinations</span>
                <span className="text-lg font-bold text-white">
                  {performanceData?.assessments_completed || 0}
                </span>
              </div>
            </div>
          </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 2: INTELLIGENT QUESTION RECOMMENDATIONS                       */}
      {/* --------------------------------------------------------------------- */}
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
              Recommended Practice Challenges
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Personalized problem recommendations tailored to your topic mastery and dynamically adjusted difficulty.
            </p>
          </div>
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            {recommendations.length} Active Challenges
          </span>
        </div>

        {recommendations.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">
            No personalized recommendations available. Complete more assessment problems to unlock targeted practice.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recommendations.map((rec) => (
              <div
                key={rec.question_id}
                className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-800/30 hover:border-orange-500/40 hover:shadow-md transition-all duration-200 flex flex-col justify-between space-y-4"
              >
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <span className="px-2 py-0.5 rounded-lg text-[11px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {rec.topic}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[11px] font-extrabold uppercase tracking-wider ${
                        rec.difficulty === "EASY"
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                          : rec.difficulty === "HARD"
                          ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
                          : "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                      }`}
                    >
                      {rec.difficulty}
                    </span>
                  </div>

                  <h3 className="font-bold text-sm text-slate-900 dark:text-white leading-snug">
                    {rec.title}
                  </h3>

                  <div className="p-3 rounded-xl bg-orange-50/60 dark:bg-orange-950/20 border border-orange-200/60 dark:border-orange-800/40 text-xs text-orange-950 dark:text-orange-200 leading-relaxed">
                    <span className="font-semibold block text-[10px] uppercase text-orange-700 dark:text-orange-400 mb-0.5">
                      Why Recommended
                    </span>
                    {rec.recommendation_reason}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400 font-medium">
                    {rec.marks} pts • {rec.time_limit_seconds}s limit
                  </span>
                  <button
                    onClick={() => handleStartPractice(rec.question_id)}
                    className="px-3.5 py-1.5 text-xs font-bold text-white bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 rounded-xl shadow-sm transition"
                  >
                    Start Practice →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 3: STRENGTHS, WEAKNESSES & LEARNING INSIGHTS                  */}
      {/* --------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Strengths & Needs Improvement Matrix (8 Cols) */}
        <div className="lg:col-span-8 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Topic Strengths & Growth Areas
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Authoritative categorization based on functional evaluation correctness and problem difficulty weighting.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Core Strengths */}
            <div className="p-4 rounded-2xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/80 dark:border-emerald-800/50 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  Strong Topics ({swData?.strong_topics.length || 0})
                </span>
              </div>

              {(!swData?.strong_topics || swData.strong_topics.length === 0) ? (
                <p className="text-xs text-slate-500 py-3 italic">
                  No topics verified as strong yet. Continue practicing to establish mastery.
                </p>
              ) : (
                <div className="space-y-2">
                  {swData.strong_topics.map((t) => (
                    <button
                      type="button"
                      key={t.topic}
                      onClick={() => handleSelectTopic(t.topic)}
                      className="w-full text-left p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-800/80 hover:border-emerald-500 hover:shadow-sm transition flex items-center justify-between text-xs cursor-pointer group"
                    >
                      <span className="font-bold text-slate-800 dark:text-slate-200 group-hover:text-emerald-600 transition">{t.topic}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-600 dark:text-emerald-400 font-bold">{t.mastery_score}%</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-300 font-semibold">
                          {t.mastery_level}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Needs Improvement */}
            <div className="p-4 rounded-2xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200/80 dark:border-amber-800/50 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Requires Improvement ({swData?.needs_improvement_topics.length || 0})
                </span>
              </div>

              {(!swData?.needs_improvement_topics || swData.needs_improvement_topics.length === 0) ? (
                <p className="text-xs text-slate-500 py-3 italic">
                  No critical topic weaknesses flagged. Keep up the high standard!
                </p>
              ) : (
                <div className="space-y-2">
                  {swData.needs_improvement_topics.map((t) => (
                    <button
                      type="button"
                      key={t.topic}
                      onClick={() => handleSelectTopic(t.topic)}
                      className="w-full text-left p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-amber-200 dark:border-amber-800/80 hover:border-amber-500 hover:shadow-sm transition flex items-center justify-between text-xs cursor-pointer group"
                    >
                      <span className="font-bold text-slate-800 dark:text-slate-200 group-hover:text-amber-600 transition">{t.topic}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-amber-600 dark:text-amber-400 font-bold">{t.mastery_score}%</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-300 font-semibold">
                          Practice {t.recommended_difficulty}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Unattempted Topics Pill Row */}
          {swData?.unattempted_topics && swData.unattempted_topics.length > 0 && (
            <div className="pt-2 space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                Unexplored Syllabus Topics ({swData.unattempted_topics.length})
              </span>
              <div className="flex flex-wrap gap-2">
                {swData.unattempted_topics.map((topic) => (
                  <button
                    type="button"
                    key={topic}
                    onClick={() => handleSelectTopic(topic)}
                    className="px-2.5 py-1 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-orange-50 dark:bg-slate-800 dark:hover:bg-orange-950/40 text-slate-600 hover:text-orange-600 dark:text-slate-300 dark:hover:text-orange-300 border border-slate-200 hover:border-orange-300 dark:border-slate-700 dark:hover:border-orange-800 transition cursor-pointer"
                  >
                    {topic} →
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Automated Learning Insights (4 Cols) */}
        <div className="lg:col-span-4 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-7 space-y-5">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <svg className="w-5 h-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Learning Insights
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Automated pedagogical observations.</p>
          </div>

          <div className="space-y-3">
            {(!swData?.insights_summary || swData.insights_summary.length === 0) ? (
              <p className="text-xs text-slate-500 py-4">No observations recorded yet.</p>
            ) : (
              swData.insights_summary.map((insight, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 leading-relaxed"
                >
                  {insight}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 4: DETAILED TOPIC MASTERY AUDIT                               */}
      {/* --------------------------------------------------------------------- */}
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Topic Mastery Progression Registry
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Transparent, explainable Bayesian skill assessment across all tracked coding concepts.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl text-xs">
            <button
              onClick={() => setActiveFilterTab("all")}
              className={`px-3 py-1 font-bold rounded-lg transition ${
                activeFilterTab === "all" ? "bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              }`}
            >
              All Topics
            </button>
            <button
              onClick={() => setActiveFilterTab("strong")}
              className={`px-3 py-1 font-bold rounded-lg transition ${
                activeFilterTab === "strong" ? "bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              }`}
            >
              Strong
            </button>
            <button
              onClick={() => setActiveFilterTab("weak")}
              className={`px-3 py-1 font-bold rounded-lg transition ${
                activeFilterTab === "weak" ? "bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              }`}
            >
              Needs Practice
            </button>
            <button
              onClick={() => setActiveFilterTab("unattempted")}
              className={`px-3 py-1 font-bold rounded-lg transition ${
                activeFilterTab === "unattempted" ? "bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              }`}
            >
              Unexplored
            </button>
          </div>
        </div>

        {/* Topic Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTopics.map((item) => (
            <div
              key={item.topic}
              onClick={() => handleSelectTopic(item.topic)}
              className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 hover:border-orange-500/50 hover:shadow-md transition-all duration-200 space-y-3 flex flex-col justify-between cursor-pointer group"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-slate-900 dark:text-white group-hover:text-orange-600 transition">{item.topic}</h3>
                    <span className="text-[11px] text-slate-400">
                      {item.questions_solved} of {item.questions_attempted} solved ({item.success_rate}%)
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-extrabold uppercase ${
                      item.mastery_level === "ADVANCED"
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                        : item.mastery_level === "PROFICIENT"
                        ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300"
                        : item.mastery_level === "DEVELOPING"
                        ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                        : "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                    }`}
                  >
                    {item.mastery_level}
                  </span>
                </div>

                {/* Mastery Progress Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                    <span>Proficiency Score</span>
                    <span>{item.mastery_score}%</span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        item.mastery_score >= 85
                          ? "bg-emerald-500"
                          : item.mastery_score >= 65
                          ? "bg-indigo-500"
                          : item.mastery_score >= 40
                          ? "bg-amber-500"
                          : "bg-slate-400"
                      }`}
                      style={{ width: `${Math.min(100, Math.max(item.mastery_score, 4))}%` }}
                    ></div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] pt-1 text-slate-500 border-t border-slate-200/80 dark:border-slate-800">
                  <span>Confidence: <strong className="text-slate-700 dark:text-slate-300">{item.confidence_level}</strong></span>
                  <span>Recommended: <strong className="text-slate-700 dark:text-slate-300">{item.recommended_difficulty}</strong></span>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectTopic(item.topic);
                  }}
                  className="w-full py-2 px-3 text-xs font-bold text-center text-orange-600 group-hover:text-white bg-orange-50 group-hover:bg-orange-600 dark:bg-orange-950/40 dark:group-hover:bg-orange-600 rounded-xl border border-orange-200 dark:border-orange-800/80 transition-all flex items-center justify-center gap-1.5 shadow-sm"
                >
                  <span>Browse & Practice Questions</span>
                  <span>→</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* SECTION 5: LONGITUDINAL MASTERY AUDIT LOG                             */}
      {/* --------------------------------------------------------------------- */}
      {historySnapshots.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-4">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
              Mastery Snapshot Audit Trail
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Chronological log of mastery recalculations triggered by examination and practice submissions.
            </p>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 max-h-56">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50/80 dark:bg-slate-800/60 font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-200 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-4 py-2.5">Timestamp</th>
                  <th className="px-4 py-2.5">Topic</th>
                  <th className="px-4 py-2.5">Mastery Score</th>
                  <th className="px-4 py-2.5">Classification</th>
                  <th className="px-4 py-2.5">Trigger Event</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 font-mono">
                {historySnapshots.map((h) => (
                  <tr key={h.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-2 text-slate-400">
                      {new Date(h.recorded_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 font-semibold text-slate-800 dark:text-slate-200">
                      {h.topic}
                    </td>
                    <td className="px-4 py-2 font-bold text-orange-600 dark:text-orange-400">
                      {h.mastery_score}%
                    </td>
                    <td className="px-4 py-2">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 font-bold">
                        {h.mastery_level}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-400 text-[11px]">{h.trigger_event}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
        </>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* PRACTICE MODAL: INTERACTIVE CODING ENVIRONMENT                        */}
      {/* --------------------------------------------------------------------- */}
      {practiceModalOpen && activePracticeQuestion && (
        <div className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-slate-900 text-white border-b border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-orange-400">
                  Targeted Practice Challenge
                </span>
                <h3 className="text-base sm:text-lg font-bold">{activePracticeQuestion.title}</h3>
              </div>
              <button
                onClick={() => setPracticeModalOpen(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                &times;
              </button>
            </div>

            {/* Modal Body: Split Question + Code */}
            <div className="p-5 flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Left Pane: Question Description (5 cols) */}
              <div className="lg:col-span-5 space-y-4 text-xs text-slate-700 dark:text-slate-300 overflow-y-auto max-h-[600px] pr-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 font-bold">
                    {activePracticeQuestion.topic}
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-orange-100 dark:bg-orange-950 text-orange-800 dark:text-orange-300 font-bold uppercase">
                    {activePracticeQuestion.difficulty}
                  </span>
                  <span className="text-slate-400">• {activePracticeQuestion.marks} pts</span>
                </div>

                <div>
                  <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px] mb-1">
                    Problem Statement
                  </h4>
                  <div className="whitespace-pre-wrap leading-relaxed bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
                    {activePracticeQuestion.problem_description}
                  </div>
                </div>

                {activePracticeQuestion.input_format && (
                  <div>
                    <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px] mb-1">
                      Input Format
                    </h4>
                    <pre className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 font-mono text-[11px] whitespace-pre-wrap">
                      {activePracticeQuestion.input_format}
                    </pre>
                  </div>
                )}

                {activePracticeQuestion.output_format && (
                  <div>
                    <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px] mb-1">
                      Output Format
                    </h4>
                    <pre className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 font-mono text-[11px] whitespace-pre-wrap">
                      {activePracticeQuestion.output_format}
                    </pre>
                  </div>
                )}

                {/* Public Sample Cases */}
                <div>
                  <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px] mb-2">
                    Sample Test Cases ({activePracticeQuestion.sample_test_cases.length})
                  </h4>
                  <div className="space-y-2">
                    {activePracticeQuestion.sample_test_cases.map((tc, idx) => (
                      <div
                        key={tc.id}
                        className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1.5"
                      >
                        <span className="font-bold text-[11px]">Sample Case #{idx + 1}</span>
                        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                          <div>
                            <span className="text-slate-400 block text-[10px]">Input:</span>
                            <pre className="p-1.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 overflow-x-auto">
                              {tc.input_data}
                            </pre>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Expected:</span>
                            <pre className="p-1.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 overflow-x-auto">
                              {tc.expected_output}
                            </pre>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Pane: Code Editor + Execution (7 cols) */}
              <div className="lg:col-span-7 flex flex-col space-y-3">
                {/* Editor Bar */}
                <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-semibold text-slate-500">Language:</label>
                    <select
                      value={practiceLanguage?.id || ""}
                      onChange={(e) => handlePracticeLanguageChange(e.target.value)}
                      className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs font-semibold"
                    >
                      {languages.map((l) => (
                        <option key={l.id} value={l.id}>
                          {l.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleRunPracticeSample}
                      disabled={practiceExecuting}
                      className="px-3.5 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 text-xs font-bold rounded-xl transition disabled:opacity-50"
                    >
                      {practiceExecuting ? "Running..." : "Run Sample"}
                    </button>
                    <button
                      onClick={handleSubmitPractice}
                      disabled={practiceExecuting}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition shadow disabled:opacity-50"
                    >
                      {practiceExecuting ? "Evaluating..." : "Submit Solution"}
                    </button>
                  </div>
                </div>

                {/* Monaco Editor */}
                <div className="h-[280px] rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-[#1e1e1e]">
                  <MonacoEditor
                    height="100%"
                    language={practiceLanguage?.name.toLowerCase().includes("java") ? "java" : "python"}
                    theme="vs-dark"
                    value={practiceCode}
                    onChange={(v) => setPracticeCode(v || "")}
                    options={{
                      fontSize: 13,
                      minimap: { enabled: false },
                      automaticLayout: true,
                    }}
                  />
                </div>

                {/* Output Console */}
                <div className="p-3.5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                    <span className="font-bold uppercase tracking-wider text-[11px] text-slate-500">
                      Practice Execution Console
                    </span>
                    {practiceResult && (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          practiceResult.status === "ACCEPTED"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                            : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                        }`}
                      >
                        {practiceResult.status} ({practiceResult.passed_test_cases}/{practiceResult.total_test_cases} passed)
                      </span>
                    )}
                  </div>

                  {practiceExecuting ? (
                    <div className="py-6 text-center text-xs text-slate-400 animate-pulse">
                      Running solution through secure sandbox...
                    </div>
                  ) : !practiceResult ? (
                    <div className="py-6 text-center text-xs text-slate-400">
                      Click &quot;Run Sample&quot; to test or &quot;Submit Solution&quot; to formally evaluate and update topic mastery.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {practiceResult.test_case_results.map((tr, i) => (
                          <div
                            key={tr.test_case_id}
                            className={`p-2 rounded-lg border text-[11px] space-y-0.5 ${
                              tr.status === "ACCEPTED"
                                ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800"
                                : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800"
                            }`}
                          >
                            <div className="flex justify-between font-bold">
                              <span>Case #{i + 1}</span>
                              <span className={tr.status === "ACCEPTED" ? "text-emerald-600" : "text-rose-600"}>
                                {tr.status}
                              </span>
                            </div>
                            {tr.error_message && <p className="text-rose-500 font-mono">{tr.error_message}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
