import { apiClient } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/tokenStorage";
import { ApiResponse } from "@/types/api";
import {
  AssessmentAdmin,
  AssessmentCreatePayload,
  AssessmentPublic,
  AssessmentStartResponse,
  AssessmentSubmitResponse,
  CohortAttemptResult,
  ProgrammingLanguageInfo,
  QuestionAdmin,
  QuestionCreatePayload,
  QuestionPublic,
  QuestionValidationResponse,
  SubmissionEvaluation,
  SubmissionResponse,
  TestCaseAdmin,
  TestCaseCategory,
} from "@/types/assessment";

function getAuthHeaders(): Record<string, string> {
  const token = tokenStorage.getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// -----------------------------------------------------------------------------
// Question Bank APIs (Instructor / Admin)
// -----------------------------------------------------------------------------

export async function listQuestionsApi(params?: {
  topic?: string;
  difficulty?: string;
  is_archived?: boolean;
  search?: string;
}): Promise<ApiResponse<QuestionAdmin[]>> {
  const searchParams = new URLSearchParams();
  if (params?.topic) searchParams.append("topic", params.topic);
  if (params?.difficulty) searchParams.append("difficulty", params.difficulty);
  if (params?.is_archived !== undefined) searchParams.append("is_archived", String(params.is_archived));
  if (params?.search) searchParams.append("search", params.search);

  const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return apiClient<QuestionAdmin[]>(`/questions${query}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function createQuestionApi(
  payload: QuestionCreatePayload
): Promise<ApiResponse<QuestionAdmin>> {
  return apiClient<QuestionAdmin>("/questions", {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function updateQuestionApi(
  questionId: string,
  payload: Partial<QuestionCreatePayload>
): Promise<ApiResponse<QuestionAdmin>> {
  return apiClient<QuestionAdmin>(`/questions/${questionId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function getQuestionApi(
  questionId: string
): Promise<ApiResponse<QuestionAdmin | QuestionPublic>> {
  return apiClient<QuestionAdmin | QuestionPublic>(`/questions/${questionId}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function archiveQuestionApi(
  questionId: string
): Promise<ApiResponse<{ detail: string }>> {
  return apiClient<{ detail: string }>(`/questions/${questionId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
}

export async function addTestCaseApi(
  questionId: string,
  testCase: {
    input_data: string;
    expected_output: string;
    explanation?: string;
    marks: number;
    display_order: number;
    is_hidden: boolean;
    category?: TestCaseCategory;
  }
): Promise<ApiResponse<TestCaseAdmin>> {
  return apiClient<TestCaseAdmin>(`/questions/${questionId}/test-cases`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(testCase),
  });
}

export async function updateTestCaseApi(
  questionId: string,
  testCaseId: string,
  testCase: Partial<TestCaseAdmin>
): Promise<ApiResponse<TestCaseAdmin>> {
  return apiClient<TestCaseAdmin>(`/questions/${questionId}/test-cases/${testCaseId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(testCase),
  });
}

export async function deleteTestCaseApi(
  questionId: string,
  testCaseId: string
): Promise<ApiResponse<{ detail: string }>> {
  return apiClient<{ detail: string }>(`/questions/${questionId}/test-cases/${testCaseId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
}

export async function validateQuestionApi(
  questionId: string
): Promise<ApiResponse<QuestionValidationResponse>> {
  return apiClient<QuestionValidationResponse>(`/questions/${questionId}/validate`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
}

// -----------------------------------------------------------------------------
// Assessment Management APIs (Instructor / Admin)
// -----------------------------------------------------------------------------

export async function listAssessmentsApi(
  statusFilter?: string
): Promise<ApiResponse<AssessmentAdmin[]>> {
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
  return apiClient<AssessmentAdmin[]>(`/assessments${query}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function createAssessmentApi(
  payload: AssessmentCreatePayload
): Promise<ApiResponse<AssessmentAdmin>> {
  return apiClient<AssessmentAdmin>("/assessments", {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function getAssessmentAdminApi(
  assessmentId: string
): Promise<ApiResponse<AssessmentAdmin>> {
  return apiClient<AssessmentAdmin>(`/assessments/${assessmentId}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function publishAssessmentApi(
  assessmentId: string
): Promise<ApiResponse<AssessmentAdmin>> {
  return apiClient<AssessmentAdmin>(`/assessments/${assessmentId}/publish`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
}

export async function assignCandidatesApi(
  assessmentId: string,
  userIds: string[]
): Promise<ApiResponse<{ detail: string; enrolled_count: number }>> {
  return apiClient<{ detail: string; enrolled_count: number }>(`/assessments/${assessmentId}/candidates`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ user_ids: userIds }),
  });
}

export async function getAssessmentCohortResultsApi(
  assessmentId: string
): Promise<ApiResponse<{ assessment_id: string; total_attempts: number; results: CohortAttemptResult[] }>> {
  return apiClient<{ assessment_id: string; total_attempts: number; results: CohortAttemptResult[] }>(
    `/assessments/${assessmentId}/results`,
    {
      method: "GET",
      headers: getAuthHeaders(),
    }
  );
}

// -----------------------------------------------------------------------------
// Student Assessment Workflow APIs
// -----------------------------------------------------------------------------

export async function listStudentLanguagesApi(): Promise<ApiResponse<ProgrammingLanguageInfo[]>> {
  return apiClient<ProgrammingLanguageInfo[]>("/student/languages", {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function listStudentAssessmentsApi(): Promise<ApiResponse<AssessmentPublic[]>> {
  return apiClient<AssessmentPublic[]>("/student/assessments", {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function startAssessmentApi(
  assessmentId: string
): Promise<ApiResponse<AssessmentStartResponse>> {
  return apiClient<AssessmentStartResponse>(`/student/assessments/${assessmentId}/start`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
}

export async function saveCodeDraftApi(
  assessmentId: string,
  payload: { question_id: string; programming_language_id: string; source_code: string }
): Promise<ApiResponse<{ updated_at: string }>> {
  return apiClient<{ updated_at: string }>(`/student/assessments/${assessmentId}/drafts`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function runSampleCodeApi(
  assessmentId: string,
  payload: { question_id: string; programming_language_id: string; source_code: string }
): Promise<ApiResponse<SubmissionResponse>> {
  return apiClient<SubmissionResponse>(`/student/assessments/${assessmentId}/run-sample`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
    timeoutMs: 20000,
  });
}

export async function submitQuestionSolutionApi(
  assessmentId: string,
  payload: { question_id: string; programming_language_id: string; source_code: string }
): Promise<ApiResponse<SubmissionResponse>> {
  return apiClient<SubmissionResponse>(`/student/assessments/${assessmentId}/submit-code`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
    timeoutMs: 30000,
  });
}

export async function finishAssessmentApi(
  assessmentId: string
): Promise<ApiResponse<AssessmentSubmitResponse>> {
  return apiClient<AssessmentSubmitResponse>(`/student/assessments/${assessmentId}/finish`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
}

export async function getMyAssessmentResultApi(
  assessmentId: string
): Promise<ApiResponse<AssessmentSubmitResponse>> {
  return apiClient<AssessmentSubmitResponse>(`/student/assessments/${assessmentId}/result`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}

export async function getSubmissionEvaluationApi(
  submissionId: string
): Promise<ApiResponse<SubmissionEvaluation>> {
  return apiClient<SubmissionEvaluation>(`/student/submissions/${submissionId}/evaluation`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
}
