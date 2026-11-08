import { apiClient } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/tokenStorage";
import { ApiResponse } from "@/types/api";
import {
  MasteryHistoryResponse,
  PracticeSubmissionRequest,
  QuestionRecommendationListResponse,
  StrengthsAndWeaknessesResponse,
  StudentPerformanceResponse,
  TopicCatalogResponse,
  TopicMasteryListResponse,
  TopicPracticeDetailResponse,
} from "@/types/adaptive";
import { QuestionPublic, SubmissionResponse } from "@/types/assessment";

function getAuthHeaders(): Record<string, string> {
  const token = tokenStorage.getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getStudentPerformanceApi(
  userId?: string
): Promise<ApiResponse<StudentPerformanceResponse>> {
  const query = userId ? `?user_id=${userId}` : "";
  return apiClient<StudentPerformanceResponse>(`/adaptive/performance${query}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function getTopicMasteryApi(
  userId?: string
): Promise<ApiResponse<TopicMasteryListResponse>> {
  const query = userId ? `?user_id=${userId}` : "";
  return apiClient<TopicMasteryListResponse>(`/adaptive/mastery${query}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function getStrengthsWeaknessesApi(
  userId?: string
): Promise<ApiResponse<StrengthsAndWeaknessesResponse>> {
  const query = userId ? `?user_id=${userId}` : "";
  return apiClient<StrengthsAndWeaknessesResponse>(`/adaptive/strengths-weaknesses${query}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function getQuestionRecommendationsApi(
  limit: number = 6,
  userId?: string
): Promise<ApiResponse<QuestionRecommendationListResponse>> {
  const searchParams = new URLSearchParams();
  searchParams.append("limit", String(limit));
  if (userId) searchParams.append("user_id", userId);

  return apiClient<QuestionRecommendationListResponse>(
    `/adaptive/recommendations?${searchParams.toString()}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

export async function getMasteryHistoryApi(
  topic?: string,
  limit: number = 50,
  userId?: string
): Promise<ApiResponse<MasteryHistoryResponse>> {
  const searchParams = new URLSearchParams();
  searchParams.append("limit", String(limit));
  if (topic) searchParams.append("topic", topic);
  if (userId) searchParams.append("user_id", userId);

  return apiClient<MasteryHistoryResponse>(
    `/adaptive/history?${searchParams.toString()}`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

export async function getPracticeQuestionApi(
  questionId: string
): Promise<ApiResponse<QuestionPublic>> {
  return apiClient<QuestionPublic>(`/adaptive/practice/${questionId}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function runPracticeSampleApi(
  questionId: string,
  payload: PracticeSubmissionRequest
): Promise<ApiResponse<SubmissionResponse>> {
  return apiClient<SubmissionResponse>(`/adaptive/practice/${questionId}/run-sample`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function submitPracticeSolutionApi(
  questionId: string,
  payload: PracticeSubmissionRequest
): Promise<ApiResponse<SubmissionResponse>> {
  return apiClient<SubmissionResponse>(`/adaptive/practice/${questionId}/submit`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function getTopicsCatalogApi(): Promise<ApiResponse<TopicCatalogResponse>> {
  return apiClient<TopicCatalogResponse>("/adaptive/topics", {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function getTopicPracticeDetailApi(
  topicName: string
): Promise<ApiResponse<TopicPracticeDetailResponse>> {
  return apiClient<TopicPracticeDetailResponse>(`/adaptive/topics/${encodeURIComponent(topicName)}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

