import { apiClient } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/tokenStorage";
import { ApiResponse } from "@/types/api";
import {
  AlertReviewPayload,
  AssessmentProctoringOverviewResponse,
  AttemptProctoringReportResponse,
  ProctoringAlertResponse,
  ProctoringEventPayload,
  ProctoringEventResponse,
  ProctoringSessionStartResponse,
  ProctoringSessionStatusResponse,
} from "@/types/proctoring";

function getAuthHeaders(): Record<string, string> {
  const token = tokenStorage.getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// -----------------------------------------------------------------------------
// Candidate APIs
// -----------------------------------------------------------------------------

export async function startProctoringSessionApi(
  assessmentId: string,
  attemptId: string
): Promise<ApiResponse<ProctoringSessionStartResponse>> {
  return apiClient<ProctoringSessionStartResponse>("/proctoring/sessions/start", {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      assessment_id: assessmentId,
      attempt_id: attemptId,
    }),
  });
}

export async function submitProctoringConsentApi(
  sessionId: string,
  consent: boolean
): Promise<ApiResponse<{ session_id: string; status: string; consent_given: boolean }>> {
  return apiClient<{ session_id: string; status: string; consent_given: boolean }>(
    `/proctoring/sessions/${sessionId}/consent`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ consent }),
    }
  );
}

export async function sendProctoringEventsApi(
  sessionId: string,
  events: ProctoringEventPayload[]
): Promise<ApiResponse<ProctoringEventResponse[]>> {
  return apiClient<ProctoringEventResponse[]>(`/proctoring/sessions/${sessionId}/events`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ events }),
  });
}

export async function sendProctoringHeartbeatApi(
  sessionId: string
): Promise<ApiResponse<{ session_id: string; last_heartbeat_at: string; status: string }>> {
  return apiClient<{ session_id: string; last_heartbeat_at: string; status: string }>(
    `/proctoring/sessions/${sessionId}/heartbeat`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({}),
    }
  );
}

export async function endProctoringSessionApi(
  sessionId: string
): Promise<ApiResponse<{ session_id: string; status: string }>> {
  return apiClient<{ session_id: string; status: string }>(
    `/proctoring/sessions/${sessionId}/end`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    }
  );
}

export async function getProctoringSessionStatusApi(
  sessionId: string
): Promise<ApiResponse<ProctoringSessionStatusResponse>> {
  return apiClient<ProctoringSessionStatusResponse>(`/proctoring/sessions/${sessionId}/status`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

// -----------------------------------------------------------------------------
// Instructor & Admin APIs
// -----------------------------------------------------------------------------

export async function getAssessmentProctoringOverviewApi(
  assessmentId: string
): Promise<ApiResponse<AssessmentProctoringOverviewResponse>> {
  return apiClient<AssessmentProctoringOverviewResponse>(
    `/proctoring/assessments/${assessmentId}/overview`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

export async function getAssessmentEventsApi(
  assessmentId: string,
  candidateId?: string,
  eventType?: string,
  severity?: string
): Promise<ApiResponse<ProctoringEventResponse[]>> {
  const params = new URLSearchParams();
  if (candidateId) params.append("candidate_id", candidateId);
  if (eventType) params.append("event_type", eventType);
  if (severity) params.append("severity", severity);
  const q = params.toString() ? `?${params.toString()}` : "";

  return apiClient<ProctoringEventResponse[]>(
    `/proctoring/assessments/${assessmentId}/events${q}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

export async function getAssessmentAlertsApi(
  assessmentId: string,
  reviewStatus?: string,
  severity?: string
): Promise<ApiResponse<ProctoringAlertResponse[]>> {
  const params = new URLSearchParams();
  if (reviewStatus) params.append("review_status", reviewStatus);
  if (severity) params.append("severity", severity);
  const q = params.toString() ? `?${params.toString()}` : "";

  return apiClient<ProctoringAlertResponse[]>(
    `/proctoring/assessments/${assessmentId}/alerts${q}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

export async function getAttemptProctoringReportApi(
  attemptId: string
): Promise<ApiResponse<AttemptProctoringReportResponse>> {
  return apiClient<AttemptProctoringReportResponse>(`/proctoring/attempts/${attemptId}/report`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function reviewProctoringAlertApi(
  alertId: string,
  payload: AlertReviewPayload
): Promise<ApiResponse<ProctoringAlertResponse>> {
  return apiClient<ProctoringAlertResponse>(`/proctoring/alerts/${alertId}/review`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
}
