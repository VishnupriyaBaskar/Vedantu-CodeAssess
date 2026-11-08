"use client";

import React, { useEffect, useState, useCallback } from "react";
import { checkBackendHealth } from "@/lib/api/health";
import { BackendHealthResponse } from "@/types/api";
import { AuthSection } from "@/components/auth/AuthSection";
import { useAuth } from "@/context/AuthContext";
import { QuestionBankSection } from "@/components/assessment/QuestionBankSection";
import { AssessmentManagementSection } from "@/components/assessment/AssessmentManagementSection";
import { StudentAssessmentWorkspace } from "@/components/assessment/StudentAssessmentWorkspace";
import { AdaptiveLearningWorkspace } from "@/components/adaptive/AdaptiveLearningWorkspace";
import { InstructorAnalyticsDashboard } from "@/components/analytics/InstructorAnalyticsDashboard";

type ConnectionStatus = "checking" | "connected" | "unavailable";
type ActiveTab = "analytics" | "assessments" | "questions" | "student_workspace" | "adaptive_learning";

export default function HomePage() {
  const { user, isAuthenticated, isInstructor, isAdmin } = useAuth();

  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [healthData, setHealthData] = useState<BackendHealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  // Tab management for instructors/admins
  const [activeTab, setActiveTab] = useState<ActiveTab>("assessments");
  // Tab management for students
  const [studentTab, setStudentTab] = useState<"assessments" | "adaptive">("assessments");

  const handleRetry = useCallback(async () => {
    setIsRetrying(true);
    setStatus("checking");
    setErrorMessage(null);

    const result = await checkBackendHealth();
    setLastChecked(new Date().toLocaleTimeString());
    setIsRetrying(false);

    if (result.success && result.data && result.data.status === "healthy") {
      setStatus("connected");
      setHealthData(result.data);
    } else {
      setStatus("unavailable");
      setHealthData(null);
      setErrorMessage(
        result.error?.message || "Could not establish a connection to the assessment backend service."
      );
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;
    const abortController = new AbortController();

    async function verifyBackendConnection() {
      const result = await checkBackendHealth({ signal: abortController.signal });
      if (isCancelled) return;

      setLastChecked(new Date().toLocaleTimeString());
      setIsRetrying(false);

      if (result.success && result.data && result.data.status === "healthy") {
        setStatus("connected");
        setHealthData(result.data);
      } else {
        setStatus("unavailable");
        setHealthData(null);
        setErrorMessage(
          result.error?.message || "Could not establish a connection to the assessment backend service."
        );
      }
    }

    verifyBackendConnection();
    return () => {
      isCancelled = true;
      abortController.abort();
    };
  }, []);

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8 flex-1">
      {/* Executive Hero Banner */}
      <section className="text-center space-y-3.5 pt-2 pb-1">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-orange-50 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300 border border-orange-200/80 dark:border-orange-800/80 mb-1">
          <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
          Enterprise Coding Assessment Engine
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Vedantu Coding Assessment Platform
        </h1>
        <p className="max-w-3xl mx-auto text-sm sm:text-base text-slate-600 dark:text-slate-400 leading-relaxed text-balance">
          Standardized programming assessments with secure multi-language sandboxes, automated deterministic grading, static code analysis, and AI-powered evaluation.
        </p>
      </section>

      {/* Authentication and Profile Overview */}
      <AuthSection />

      {/* Main Workspace for Authenticated Users */}
      {isAuthenticated && (
        <div className="space-y-6">
          {/* Instructor & Admin Navigation Tabs */}
          {isInstructor || isAdmin ? (
            <div className="space-y-6">
              <div className="bg-slate-100 dark:bg-slate-800/60 p-1.5 rounded-2xl flex flex-wrap gap-1 border border-slate-200 dark:border-slate-700/60">
                <button
                  type="button"
                  onClick={() => setActiveTab("assessments")}
                  className={`flex-1 min-w-[170px] py-2.5 px-4 text-xs sm:text-sm font-bold rounded-xl transition-all ${
                    activeTab === "assessments"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  Assessment Management
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("analytics")}
                  className={`flex-1 min-w-[170px] py-2.5 px-4 text-xs sm:text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === "analytics"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
                  Analytics & Insights
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("questions")}
                  className={`flex-1 min-w-[170px] py-2.5 px-4 text-xs sm:text-sm font-bold rounded-xl transition-all ${
                    activeTab === "questions"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  Question Bank
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("student_workspace")}
                  className={`flex-1 min-w-[180px] py-2.5 px-4 text-xs sm:text-sm font-bold rounded-xl transition-all ${
                    activeTab === "student_workspace"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  Candidate Assessment Workspace
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("adaptive_learning")}
                  className={`flex-1 min-w-[180px] py-2.5 px-4 text-xs sm:text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === "adaptive_learning"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                  Adaptive Learning Engine
                </button>
              </div>

              {activeTab === "assessments" && <AssessmentManagementSection />}
              {activeTab === "analytics" && <InstructorAnalyticsDashboard />}
              {activeTab === "questions" && <QuestionBankSection />}
              {activeTab === "student_workspace" && <StudentAssessmentWorkspace />}
              {activeTab === "adaptive_learning" && <AdaptiveLearningWorkspace />}
            </div>
          ) : (
            /* Student Assessment & Adaptive Learning Workspace */
            <div className="space-y-6">
              <div className="bg-slate-100 dark:bg-slate-800/60 p-1.5 rounded-2xl flex flex-wrap gap-1 border border-slate-200 dark:border-slate-700/60 max-w-lg mx-auto sm:mx-0">
                <button
                  type="button"
                  onClick={() => setStudentTab("assessments")}
                  className={`flex-1 py-2.5 px-4 text-xs sm:text-sm font-bold rounded-xl transition-all ${
                    studentTab === "assessments"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  Timed Examinations
                </button>
                <button
                  type="button"
                  onClick={() => setStudentTab("adaptive")}
                  className={`flex-1 py-2.5 px-4 text-xs sm:text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 ${
                    studentTab === "adaptive"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                  Adaptive Learning & Practice
                </button>
              </div>

              {studentTab === "assessments" ? <StudentAssessmentWorkspace /> : <AdaptiveLearningWorkspace />}
            </div>
          )}
        </div>
      )}

      {/* Platform Operational Telemetry Footer Card */}
      <section
        aria-labelledby="system-status-heading"
        className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-colors"
      >
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 id="system-status-heading" className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Platform Operational Telemetry
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Live status of evaluation clusters, PostgreSQL data stores, and execution sandboxes.
            </p>
          </div>
          <button
            onClick={handleRetry}
            disabled={isRetrying || status === "checking"}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition disabled:opacity-50 border border-slate-200 dark:border-slate-700"
          >
            {isRetrying ? "Verifying..." : "Refresh Status"}
          </button>
        </div>

        <div className="px-6 py-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2.5">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  status === "connected"
                    ? "bg-emerald-500"
                    : status === "checking"
                    ? "bg-amber-500 animate-ping"
                    : "bg-rose-500"
                }`}
              />
              <span className="text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200">
                {status === "connected"
                  ? "All Core Assessment & Execution Services Operational"
                  : status === "checking"
                  ? "Verifying platform services..."
                  : "Platform Service Unavailable"}
              </span>
            </div>

            {lastChecked && (
              <span className="text-xs text-slate-400 font-mono">
                Verified: {lastChecked}
              </span>
            )}
          </div>

          {errorMessage && (
            <p className="text-xs text-rose-500 dark:text-rose-400 mt-2 font-mono bg-rose-50 dark:bg-rose-950/40 p-2.5 rounded-lg border border-rose-200 dark:border-rose-900">
              {errorMessage}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
