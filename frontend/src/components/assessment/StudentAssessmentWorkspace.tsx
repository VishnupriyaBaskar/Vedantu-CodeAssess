"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import {
  finishAssessmentApi,
  listStudentAssessmentsApi,
  listStudentLanguagesApi,
  runSampleCodeApi,
  saveCodeDraftApi,
  startAssessmentApi,
  submitQuestionSolutionApi,
} from "@/lib/api/assessment";
import {
  AssessmentPublic,
  AssessmentStartResponse,
  AssessmentSubmitResponse,
  ProgrammingLanguageInfo,
  QuestionPublic,
  SubmissionResponse,
} from "@/types/assessment";
import { CandidateProctoringPanel } from "@/components/proctoring/CandidateProctoringPanel";

// Dynamic Monaco Editor import for Next.js SSR compatibility
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const BOILERPLATE_PYTHON = `import sys

def solve():
    # Read standard input and print output
    lines = sys.stdin.read().split()
    if not lines:
        return
    # Your logic here
    print(" ".join(lines))

if __name__ == "__main__":
    solve()
`;

const BOILERPLATE_JAVA = `import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        // Your logic here
        while (scanner.hasNext()) {
            System.out.println(scanner.next());
        }
    }
}
`;

export function StudentAssessmentWorkspace() {
  const [availableAssessments, setAvailableAssessments] = useState<AssessmentPublic[]>([]);
  const [languages, setLanguages] = useState<ProgrammingLanguageInfo[]>([]);
  const [loading, setLoading] = useState(true);

  // Active Assessment State
  const [activeExam, setActiveExam] = useState<AssessmentStartResponse | null>(null);
  const [selectedQuestionIndex, setSelectedQuestionIndex] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState<ProgrammingLanguageInfo | null>(null);
  const [sourceCode, setSourceCode] = useState<string>("");
  const [remainingSeconds, setRemainingSeconds] = useState<number>(0);
  const [isGracePeriod, setIsGracePeriod] = useState<boolean>(false);

  // Evaluation & Autosave State
  const [autosaveStatus, setAutosaveStatus] = useState<string>("Saved");
  const [isExecuting, setIsExecuting] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState<SubmissionResponse | null>(null);
  const [activeOutputTab, setActiveOutputTab] = useState<"tests" | "static" | "ai">("tests");
  const [finalScorecard, setFinalScorecard] = useState<AssessmentSubmitResponse | null>(null);

  // Finish confirmation modal
  const [showFinishConfirm, setShowFinishConfirm] = useState(false);

  // Debounced autosave ref
  const autosaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  const loadInitialData = useCallback(async () => {
    const [assRes, langRes] = await Promise.all([
      listStudentAssessmentsApi(),
      listStudentLanguagesApi(),
    ]);

    if (assRes.success && assRes.data) {
      setAvailableAssessments(assRes.data);
    }
    if (langRes.success && langRes.data) {
      setLanguages(langRes.data);
      if (langRes.data.length > 0) {
        setSelectedLanguage(langRes.data[0]);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await loadInitialData();
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [loadInitialData]);

  const handleAutoSubmit = useCallback(async () => {
    if (!activeExam) return;
    const res = await finishAssessmentApi(activeExam.assessment_id);
    if (res.success && res.data) {
      setFinalScorecard(res.data);
    }
  }, [activeExam]);

  // Timer countdown
  useEffect(() => {
    if (!activeExam || finalScorecard) return;

    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          if (!isGracePeriod) {
            setIsGracePeriod(true);
            return 15; // 15-second network grace period
          } else {
            clearInterval(timer);
            handleAutoSubmit();
            return 0;
          }
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [activeExam, isGracePeriod, finalScorecard, handleAutoSubmit]);

  const handleStartExam = async (assessmentId: string) => {
    setLoading(true);
    const res = await startAssessmentApi(assessmentId);
    if (res.success && res.data) {
      setActiveExam(res.data);
      setRemainingSeconds(res.data.remaining_seconds);
      setIsGracePeriod(false);
      setSelectedQuestionIndex(0);

      // Load code draft for first question if available
      const firstQ = res.data.questions[0];
      if (firstQ) {
        const draft = res.data.drafts[firstQ.id];
        setSourceCode(draft || BOILERPLATE_PYTHON);
      }
    } else {
      alert(res.error?.message || "Failed to start assessment.");
    }
    setLoading(false);
  };

  const handleQuestionSelect = (index: number) => {
    if (!activeExam) return;
    setSelectedQuestionIndex(index);
    setEvaluationResult(null);

    const targetQ = activeExam.questions[index];
    if (targetQ) {
      const draft = activeExam.drafts[targetQ.id];
      if (draft) {
        setSourceCode(draft);
      } else {
        const isJava = selectedLanguage?.name.toLowerCase().includes("java");
        setSourceCode(isJava ? BOILERPLATE_JAVA : BOILERPLATE_PYTHON);
      }
    }
  };

  const handleLanguageChange = (langId: string) => {
    const lang = languages.find((l) => l.id === langId);
    if (!lang) return;
    setSelectedLanguage(lang);

    // Switch boilerplate if currently empty or default
    const isJava = lang.name.toLowerCase().includes("java");
    if (sourceCode === BOILERPLATE_PYTHON && isJava) {
      setSourceCode(BOILERPLATE_JAVA);
    } else if (sourceCode === BOILERPLATE_JAVA && !isJava) {
      setSourceCode(BOILERPLATE_PYTHON);
    }
  };

  const triggerAutosave = useCallback((code: string) => {
    if (!activeExam || !selectedLanguage) return;
    const currentQ = activeExam.questions[selectedQuestionIndex];
    if (!currentQ) return;

    setAutosaveStatus("Saving draft...");
    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current);
    }

    autosaveTimerRef.current = setTimeout(async () => {
      const res = await saveCodeDraftApi(activeExam.assessment_id, {
        question_id: currentQ.id,
        programming_language_id: selectedLanguage.id,
        source_code: code,
      });

      if (res.success) {
        setAutosaveStatus("Draft autosaved");
        // Update local drafts record
        activeExam.drafts[currentQ.id] = code;
      } else {
        setAutosaveStatus("Failed to save draft");
      }
    }, 2000);
  }, [activeExam, selectedLanguage, selectedQuestionIndex]);

  const handleCodeChange = (value: string | undefined) => {
    const newCode = value || "";
    setSourceCode(newCode);
    triggerAutosave(newCode);
  };

  const handleRunSampleCode = async () => {
    if (!activeExam || !selectedLanguage) return;
    const currentQ = activeExam.questions[selectedQuestionIndex];
    if (!currentQ) return;

    setIsExecuting(true);
    setEvaluationResult(null);

    const res = await runSampleCodeApi(activeExam.assessment_id, {
      question_id: currentQ.id,
      programming_language_id: selectedLanguage.id,
      source_code: sourceCode,
    });

    if (res.success && res.data) {
      setEvaluationResult(res.data);
    } else {
      alert(res.error?.message || "Sample code execution failed.");
    }
    setIsExecuting(false);
  };

  const handleSubmitSolution = async () => {
    if (!activeExam || !selectedLanguage) return;
    const currentQ = activeExam.questions[selectedQuestionIndex];
    if (!currentQ) return;

    setIsExecuting(true);
    setEvaluationResult(null);

    const res = await submitQuestionSolutionApi(activeExam.assessment_id, {
      question_id: currentQ.id,
      programming_language_id: selectedLanguage.id,
      source_code: sourceCode,
    });

    if (res.success && res.data) {
      setEvaluationResult(res.data);
    } else {
      alert(res.error?.message || "Solution evaluation failed.");
    }
    setIsExecuting(false);
  };

  const handleManualFinish = async () => {
    if (!activeExam) return;
    setShowFinishConfirm(false);
    setLoading(true);

    const res = await finishAssessmentApi(activeExam.assessment_id);
    if (res.success && res.data) {
      setFinalScorecard(res.data);
    } else {
      alert(res.error?.message || "Failed to finalize examination.");
    }
    setLoading(false);
  };

  // Format timer
  const formatTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  // ---------------------------------------------------------------------------
  // View 1: Available Assessments List
  // ---------------------------------------------------------------------------
  if (!activeExam) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Available Assessments
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Select an active examination below to begin or resume your timed assessment session.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              {availableAssessments.length} Active {availableAssessments.length === 1 ? "Session" : "Sessions"}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-sm text-slate-500 space-y-3">
            <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p>Loading available assessment sessions...</p>
          </div>
        ) : availableAssessments.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-500 max-w-md mx-auto space-y-2">
            <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="font-semibold text-slate-700 dark:text-slate-300">No Assessments Scheduled</p>
            <p className="text-xs text-slate-400">There are currently no active coding examinations assigned to your account.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {availableAssessments.map((a) => (
              <div
                key={a.id}
                className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-800/30 hover:border-orange-500/30 hover:shadow-md transition-all duration-200 flex flex-col justify-between space-y-4"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-bold text-base text-slate-900 dark:text-white leading-snug">
                      {a.title}
                    </h3>
                    <span
                      className={`shrink-0 px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide uppercase ${
                        a.difficulty === "EASY"
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                          : a.difficulty === "HARD"
                          ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
                          : "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                      }`}
                    >
                      {a.difficulty}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                    {a.description || a.instructions || "Standard timed coding evaluation."}
                  </p>
                </div>

                <div className="space-y-3 pt-2">
                  <div className="grid grid-cols-3 gap-2 text-center py-2.5 px-3 rounded-xl bg-slate-100/60 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-800 text-xs">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 block tracking-wider">Duration</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200">{a.duration_minutes}m</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 block tracking-wider">Problems</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200">{a.question_count}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 block tracking-wider">Passing</span>
                      <span className="font-bold text-slate-800 dark:text-slate-200">{a.passing_marks}/{a.total_marks}</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-1">
                    <span className="text-xs text-slate-400 font-medium">
                      {a.has_attempted ? `Status: ${a.attempt_status}` : "Ready to Start"}
                    </span>
                    {a.attempt_status === "COMPLETED" ? (
                      <span className="px-3.5 py-1.5 text-xs font-semibold text-slate-500 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        Completed
                      </span>
                    ) : (
                      <button
                        onClick={() => handleStartExam(a.id)}
                        className="px-4 py-2 text-xs font-bold text-white bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 rounded-xl shadow-sm hover:shadow transition-all duration-150"
                      >
                        {a.has_attempted ? "Resume Assessment" : "Start Assessment"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // View 2: Final Scorecard View
  // ---------------------------------------------------------------------------
  if (finalScorecard) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-xl p-8 sm:p-10 max-w-xl mx-auto space-y-7 text-center">
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2">
            <span
              className={`inline-block px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-widest border ${
                finalScorecard.is_passed
                  ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700"
                  : "bg-rose-50 text-rose-800 dark:bg-rose-950/70 dark:text-rose-300 border-rose-300 dark:border-rose-700"
              }`}
            >
              {finalScorecard.is_passed ? "ASSESSMENT PASSED" : "ASSESSMENT COMPLETED"}
            </span>
          </div>

          <h2 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Evaluation Report & Scorecard
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
            Your final solutions have been compiled, executed across verified test suites, and logged to the central assessment gradebook.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3 p-5 rounded-2xl bg-slate-50/70 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700">
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Score</span>
            <span className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {finalScorecard.total_score}
              <span className="text-xs text-slate-400 font-normal ml-1">/ {finalScorecard.total_possible_marks}</span>
            </span>
          </div>
          <div className="space-y-1 border-x border-slate-200 dark:border-slate-700">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Percentage</span>
            <span className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {finalScorecard.percentage}%
            </span>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Outcome</span>
            <span
              className={`text-2xl font-extrabold ${
                finalScorecard.is_passed ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
              }`}
            >
              {finalScorecard.is_passed ? "PASS" : "FAIL"}
            </span>
          </div>
        </div>

        <div>
          <button
            onClick={() => {
              setActiveExam(null);
              setFinalScorecard(null);
              loadInitialData();
            }}
            className="w-full sm:w-auto px-8 py-3 bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-slate-100 dark:text-slate-900 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition shadow-md"
          >
            Return to Assessments Dashboard
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // View 3: Live Student Examination Workspace
  // ---------------------------------------------------------------------------
  const currentQuestion: QuestionPublic | undefined = activeExam.questions[selectedQuestionIndex];

  return (
    <div className="space-y-4">
      {/* Candidate Proctoring Bar & Active Integrity Monitoring */}
      <CandidateProctoringPanel
        assessmentId={activeExam.assessment_id}
        attemptId={activeExam.attempt_id}
        isExamCompleted={!!finalScorecard}
      />

      {/* Top Examination Bar */}
      <div className="bg-slate-900 border border-slate-800 text-white rounded-2xl p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4 shadow-lg">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <h1 className="text-base sm:text-lg font-bold tracking-tight">{activeExam.title}</h1>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>
              Problem <strong className="text-slate-200">{selectedQuestionIndex + 1}</strong> of{" "}
              <strong className="text-slate-200">{activeExam.questions.length}</strong>
            </span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1.5">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  autosaveStatus.includes("Saving")
                    ? "bg-amber-400 animate-spin"
                    : autosaveStatus.includes("Failed")
                    ? "bg-rose-500"
                    : "bg-emerald-400"
                }`}
              ></span>
              <span className="font-mono text-[11px] text-slate-300">{autosaveStatus}</span>
            </span>
          </div>
        </div>

        {/* Timer and Finish Button */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div
            className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-xs sm:text-sm font-mono font-bold tracking-wider ${
              isGracePeriod
                ? "bg-rose-950/80 border-rose-500/80 text-rose-300 animate-pulse shadow-sm shadow-rose-900/50"
                : remainingSeconds <= 300
                ? "bg-amber-950/80 border-amber-500/80 text-amber-300 shadow-sm shadow-amber-900/40"
                : "bg-slate-800/90 border-slate-700/80 text-slate-100"
            }`}
          >
            <svg className="w-4 h-4 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{isGracePeriod ? `Grace: ${remainingSeconds}s` : formatTime(remainingSeconds)}</span>
          </div>

          <button
            onClick={() => setShowFinishConfirm(true)}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition shadow hover:shadow-rose-900/40"
          >
            Finish Exam
          </button>
        </div>
      </div>

      {/* Main Split Layout: Problem Statement + Monaco Code Editor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Pane: Question Details & Test Cases (5 Cols) */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 space-y-5 overflow-y-auto max-h-[750px]">
          {/* Question Navigator */}
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            {activeExam.questions.map((q, idx) => (
              <button
                key={q.id}
                onClick={() => handleQuestionSelect(idx)}
                className={`px-3 py-1.5 text-xs font-bold rounded-xl transition ${
                  selectedQuestionIndex === idx
                    ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-sm"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                }`}
              >
                P{idx + 1} ({q.marks} pts)
              </button>
            ))}
          </div>

          {currentQuestion ? (
            <div className="space-y-4 text-sm text-slate-700 dark:text-slate-300">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
                    {currentQuestion.title}
                  </h2>
                  <span
                    className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wide uppercase ${
                      currentQuestion.difficulty === "EASY"
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                        : currentQuestion.difficulty === "HARD"
                        ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
                        : "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                    }`}
                  >
                    {currentQuestion.difficulty}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-2">
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 font-medium">
                    {currentQuestion.topic}
                  </span>
                  <span>•</span>
                  <span>Time Limit: <strong className="text-slate-700 dark:text-slate-300">{currentQuestion.time_limit_seconds}s</strong></span>
                  <span>•</span>
                  <span>Memory Limit: <strong className="text-slate-700 dark:text-slate-300">{currentQuestion.memory_limit_mb}MB</strong></span>
                </div>
              </div>

              {/* Problem Statement */}
              <div>
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Problem Description
                </h3>
                <div className="whitespace-pre-wrap leading-relaxed text-slate-800 dark:text-slate-200 bg-slate-50/60 dark:bg-slate-800/30 p-3.5 rounded-xl border border-slate-200/80 dark:border-slate-800">
                  {currentQuestion.problem_description}
                </div>
              </div>

              {currentQuestion.input_format && (
                <div>
                  <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Input Format
                  </h3>
                  <div className="whitespace-pre-wrap text-xs bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                    {currentQuestion.input_format}
                  </div>
                </div>
              )}

              {currentQuestion.output_format && (
                <div>
                  <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Output Format
                  </h3>
                  <div className="whitespace-pre-wrap text-xs bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                    {currentQuestion.output_format}
                  </div>
                </div>
              )}

              {currentQuestion.constraints && (
                <div>
                  <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Constraints
                  </h3>
                  <div className="whitespace-pre-wrap text-xs bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                    {currentQuestion.constraints}
                  </div>
                </div>
              )}

              {/* Public Sample Test Cases */}
              <div>
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Sample Test Cases ({currentQuestion.sample_test_cases.length})
                </h3>
                <div className="space-y-3">
                  {currentQuestion.sample_test_cases.map((tc, idx) => (
                    <div
                      key={tc.id}
                      className="p-3.5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700 text-xs space-y-2"
                    >
                      <span className="font-bold text-slate-800 dark:text-slate-200 text-xs">
                        Sample Case #{idx + 1}
                      </span>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="text-[11px] text-slate-400 block mb-1">Input:</span>
                          <pre className="p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg font-mono text-xs overflow-x-auto">
                            {tc.input_data}
                          </pre>
                        </div>
                        <div>
                          <span className="text-[11px] text-slate-400 block mb-1">Expected Output:</span>
                          <pre className="p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg font-mono text-xs overflow-x-auto">
                            {tc.expected_output}
                          </pre>
                        </div>
                      </div>
                      {tc.explanation && (
                        <p className="text-slate-500 dark:text-slate-400 italic text-[11px] mt-1">
                          Explanation: {tc.explanation}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-8 text-center">No question selected.</p>
          )}
        </div>

        {/* Right Pane: Monaco Code Editor & Execution Console (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          {/* Editor Header Bar */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Language:
              </label>
              <select
                value={selectedLanguage?.id || ""}
                onChange={(e) => handleLanguageChange(e.target.value)}
                className="bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs font-semibold text-slate-900 dark:text-white"
              >
                {languages.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name} ({l.version})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleRunSampleCode}
                disabled={isExecuting}
                className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold rounded-xl border border-slate-200 dark:border-slate-700 transition disabled:opacity-50"
              >
                {isExecuting ? "Executing..." : "Run Sample Code"}
              </button>
              <button
                onClick={handleSubmitSolution}
                disabled={isExecuting}
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition shadow disabled:opacity-50"
              >
                {isExecuting ? "Evaluating..." : "Submit Solution"}
              </button>
            </div>
          </div>

          {/* Monaco Editor Container */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm bg-[#1e1e1e] h-[400px]">
            <MonacoEditor
              height="100%"
              language={selectedLanguage?.name.toLowerCase().includes("java") ? "java" : "python"}
              theme="vs-dark"
              value={sourceCode}
              onChange={handleCodeChange}
              options={{
                fontSize: 13,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                automaticLayout: true,
                tabSize: 4,
              }}
            />
          </div>

          {/* Execution Output Console */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 space-y-3 min-h-[220px]">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
              <span className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Execution Output & Verification
              </span>
              {evaluationResult && (
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase ${
                    evaluationResult.status === "ACCEPTED"
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800"
                      : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border border-rose-300 dark:border-rose-800"
                  }`}
                >
                  {evaluationResult.status} ({evaluationResult.passed_test_cases}/{evaluationResult.total_test_cases} passed)
                </span>
              )}
            </div>

            {/* Evaluation Tabs: Test Cases | Static Analysis | AI Code Review */}
            <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2 text-xs">
              <button
                type="button"
                onClick={() => setActiveOutputTab("tests")}
                className={`px-3 py-1 font-semibold rounded-lg transition ${
                  activeOutputTab === "tests"
                    ? "bg-slate-800 text-white dark:bg-slate-700"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Test Cases
              </button>
              <button
                type="button"
                onClick={() => setActiveOutputTab("static")}
                className={`px-3 py-1 font-semibold rounded-lg transition flex items-center gap-1.5 ${
                  activeOutputTab === "static"
                    ? "bg-slate-800 text-white dark:bg-slate-700"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                <span>Static Analysis</span>
                {evaluationResult?.evaluation?.static_analysis && (
                  <span className="px-1.5 py-0.2 bg-indigo-500/20 text-indigo-400 text-[10px] rounded-full">
                    {evaluationResult.evaluation.static_analysis.maintainability_score}%
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveOutputTab("ai")}
                className={`px-3 py-1 font-semibold rounded-lg transition flex items-center gap-1.5 ${
                  activeOutputTab === "ai"
                    ? "bg-slate-800 text-white dark:bg-slate-700"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                <span>AI Code Review</span>
                {evaluationResult?.evaluation?.ai_status && (
                  <span className="px-1.5 py-0.2 bg-emerald-500/20 text-emerald-400 text-[10px] rounded-full">
                    {evaluationResult.evaluation.ai_provider}
                  </span>
                )}
              </button>
            </div>

            {isExecuting ? (
              <div className="py-8 text-center text-xs text-slate-500 animate-pulse space-y-2">
                <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p>Evaluating code in secure sandbox environment... Please wait.</p>
              </div>
            ) : !evaluationResult ? (
              <div className="py-6 text-center text-xs text-slate-400">
                Click &quot;Run Sample Code&quot; to test against public samples, or &quot;Submit Solution&quot; to verify against all evaluation cases.
              </div>
            ) : activeOutputTab === "tests" ? (
              <div className="space-y-2 text-xs">
                <div className="flex gap-4 text-slate-500 pb-1">
                  <span>Score Awarded: <strong>{evaluationResult.score} pts</strong></span>
                  {evaluationResult.execution_time && (
                    <span>Max Time: <strong>{evaluationResult.execution_time}s</strong></span>
                  )}
                  {evaluationResult.memory_usage && (
                    <span>Max Memory: <strong>{evaluationResult.memory_usage} KB</strong></span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {evaluationResult.test_case_results.map((tr, i) => (
                    <div
                      key={tr.test_case_id}
                      className={`p-2.5 rounded-lg border text-xs space-y-1 ${
                        tr.status === "ACCEPTED"
                          ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800"
                          : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800"
                      }`}
                    >
                      <div className="flex justify-between items-center font-bold">
                        <span>
                          {tr.is_sample ? `Sample Case #${i + 1}` : `Evaluation Case #${i + 1}`}
                        </span>
                        <span
                          className={tr.status === "ACCEPTED" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}
                        >
                          {tr.status}
                        </span>
                      </div>
                      {tr.error_message && (
                        <p className="text-rose-600 dark:text-rose-400 font-mono text-[11px]">
                          {tr.error_message}
                        </p>
                      )}
                      {tr.sample_input && (
                        <div className="text-[11px] text-slate-500 font-mono">
                          Input: {tr.sample_input} | Expected: {tr.sample_expected}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : activeOutputTab === "static" ? (
              /* Tab 2: Static Analysis Findings */
              !evaluationResult.evaluation?.static_analysis ? (
                <div className="py-6 text-center text-xs text-slate-400">
                  Static code analysis is generated upon formal &quot;Submit Solution&quot;.
                </div>
              ) : (
                <div className="space-y-3 text-xs">
                  {/* Summary Metric Pills */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Maintainability</span>
                      <strong className="text-base font-bold text-orange-600 dark:text-orange-400">
                        {evaluationResult.evaluation.static_analysis.maintainability_score} / 100
                      </strong>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Complexity (CC)</span>
                      <strong className="text-base font-bold text-slate-700 dark:text-slate-300">
                        {evaluationResult.evaluation.static_analysis.cyclomatic_complexity}
                      </strong>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Lines of Code</span>
                      <strong className="text-base font-bold text-slate-700 dark:text-slate-300">
                        {evaluationResult.evaluation.static_analysis.lines_of_code}
                      </strong>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Max Nesting</span>
                      <strong className="text-base font-bold text-slate-700 dark:text-slate-300">
                        {evaluationResult.evaluation.static_analysis.max_nesting_depth}
                      </strong>
                    </div>
                  </div>

                  {/* Findings List */}
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {evaluationResult.evaluation.static_analysis.findings.length === 0 ? (
                      <p className="text-emerald-600 dark:text-emerald-400 py-3 text-center font-medium">
                        ✓ No code smells or convention violations detected. Clean implementation!
                      </p>
                    ) : (
                      evaluationResult.evaluation.static_analysis.findings.map((f, idx) => (
                        <div
                          key={idx}
                          className={`p-2.5 rounded-xl border text-xs space-y-0.5 ${
                            f.severity === "WARNING"
                              ? "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300"
                              : f.severity === "ERROR"
                              ? "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
                              : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300"
                          }`}
                        >
                          <div className="flex items-center justify-between font-semibold text-[11px]">
                            <span>
                              [{f.severity}] {f.code}
                            </span>
                            {f.line_number && <span>Line {f.line_number}</span>}
                          </div>
                          <p>{f.message}</p>
                          {f.suggestion && (
                            <p className="text-[10px] opacity-80 italic">Tip: {f.suggestion}</p>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )
            ) : (
              /* Tab 3: AI Qualitative Feedback */
              !evaluationResult.evaluation?.ai_feedback ? (
                <div className="py-6 text-center text-xs text-slate-400 space-y-1">
                  <p>AI qualitative review is generated upon formal &quot;Submit Solution&quot;.</p>
                  {evaluationResult.evaluation?.ai_status && (
                    <span className="text-[11px] text-slate-500">
                      Status: {evaluationResult.evaluation.ai_status} (Provider: {evaluationResult.evaluation.ai_provider})
                    </span>
                  )}
                </div>
              ) : (
                <div className="space-y-3 text-xs max-h-56 overflow-y-auto">
                  {/* Approach & Complexity Header */}
                  <div className="p-3 rounded-xl bg-orange-50 dark:bg-orange-950/20 border border-orange-200 dark:border-orange-800/60 space-y-1.5">
                    <div className="flex items-center justify-between font-bold text-orange-900 dark:text-orange-200">
                      <span>Algorithmic Approach</span>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 bg-orange-100 dark:bg-orange-900/60 text-orange-800 dark:text-orange-300 rounded-md">
                        {evaluationResult.evaluation.ai_feedback.estimated_time_complexity || "O(N)"} time /{" "}
                        {evaluationResult.evaluation.ai_feedback.estimated_space_complexity || "O(1)"} space
                      </span>
                    </div>
                    <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
                      {evaluationResult.evaluation.ai_feedback.logical_approach}
                    </p>
                  </div>

                  {/* Readability & Maintainability */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1">
                      <span className="font-semibold text-slate-800 dark:text-slate-200 block text-[11px]">
                        Readability
                      </span>
                      <p className="text-slate-600 dark:text-slate-400 text-[11px] leading-relaxed">
                        {evaluationResult.evaluation.ai_feedback.readability}
                      </p>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1">
                      <span className="font-semibold text-slate-800 dark:text-slate-200 block text-[11px]">
                        Maintainability
                      </span>
                      <p className="text-slate-600 dark:text-slate-400 text-[11px] leading-relaxed">
                        {evaluationResult.evaluation.ai_feedback.maintainability}
                      </p>
                    </div>
                  </div>

                  {/* Improvement Suggestions */}
                  {evaluationResult.evaluation.ai_feedback.improvement_suggestions.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="font-semibold text-slate-800 dark:text-slate-200 block text-[11px]">
                        Optimization & Best Practice Recommendations:
                      </span>
                      <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400 text-[11px]">
                        {evaluationResult.evaluation.ai_feedback.improvement_suggestions.map(
                          (tip, idx) => (
                            <li key={idx}>{tip}</li>
                          )
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        </div>
      </div>

      {/* Finish Confirmation Modal */}
      {showFinishConfirm && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl max-w-md w-full p-6 sm:p-7 space-y-4 text-center">
            <div className="w-12 h-12 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800/60 flex items-center justify-center mx-auto text-rose-600 dark:text-rose-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Finalize and Submit Examination?
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Once submitted, your final examination answers and automated evaluations will be finalized and recorded. You cannot modify code after submission.
              </p>
            </div>
            <div className="flex justify-center gap-3 pt-2">
              <button
                onClick={() => setShowFinishConfirm(false)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                Continue Working
              </button>
              <button
                onClick={handleManualFinish}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition shadow"
              >
                Yes, Submit Final Exam
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
