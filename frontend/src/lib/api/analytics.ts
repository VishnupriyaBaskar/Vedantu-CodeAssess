/**
 * Analytics and Reporting API Client
 * Project: Vedantu Online Coding Assessment Platform (Phase 8)
 * Workspace: E:\VedantuCodingPlatform_New
 */

import { config } from "@/config";
import { apiClient } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/tokenStorage";
import {
  AssessmentAnalyticsResponse,
  CandidatePerformanceDetailResponse,
  CohortAnalyticsResponse,
  InstructorOverviewKPIs,
  QuestionPerformanceItem,
} from "@/types/analytics";
import { ApiResponse } from "@/types/api";

function getAuthHeaders(): Record<string, string> {
  const token = tokenStorage.getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Fetch live high-level overview KPIs for instructors.
 */
export async function getInstructorOverviewApi(): Promise<ApiResponse<InstructorOverviewKPIs>> {
  return apiClient<InstructorOverviewKPIs>("/analytics/instructor/overview", {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

/**
 * Fetch detailed analytics for a specific assessment.
 */
export async function getAssessmentAnalyticsApi(
  assessmentId: string
): Promise<ApiResponse<AssessmentAnalyticsResponse>> {
  return apiClient<AssessmentAnalyticsResponse>(
    `/analytics/instructor/assessments/${assessmentId}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

/**
 * Fetch cohort-level proficiencies and distributions across students.
 */
export async function getCohortAnalyticsApi(): Promise<ApiResponse<CohortAnalyticsResponse>> {
  return apiClient<CohortAnalyticsResponse>("/analytics/instructor/cohort", {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

/**
 * Fetch comprehensive individual candidate performance report.
 */
export async function getCandidateReportApi(
  candidateId: string
): Promise<ApiResponse<CandidatePerformanceDetailResponse>> {
  return apiClient<CandidatePerformanceDetailResponse>(
    `/analytics/instructor/candidates/${candidateId}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

/**
 * Fetch question bank quality metrics and test case distributions.
 */
export async function getQuestionsPerformanceApi(): Promise<
  ApiResponse<QuestionPerformanceItem[]>
> {
  return apiClient<QuestionPerformanceItem[]>("/analytics/instructor/questions", {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

/**
 * Trigger authenticated browser download for CSV export endpoints.
 */
export async function downloadAnalyticsCsv(
  endpoint: string,
  filename: string
): Promise<{ success: boolean; error?: string }> {
  const baseUrl = config.apiBaseUrl.replace(/\/+$/, "");
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "text/csv",
        ...getAuthHeaders(),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      return { success: false, error: `Failed to download CSV: HTTP ${res.status}` };
    }

    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);

    return { success: true };
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to download CSV file.",
    };
  }
}
