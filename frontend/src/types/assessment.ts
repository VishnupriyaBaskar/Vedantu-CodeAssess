export type DifficultyLevel = "EASY" | "MEDIUM" | "HARD";
export type AssessmentStatus = "DRAFT" | "PUBLISHED" | "IN_PROGRESS" | "COMPLETED" | "ARCHIVED";

export interface ProgrammingLanguageInfo {
  id: string;
  name: string;
  version: string;
  judge0_language_id: number;
}

export type TestCaseCategory = "SAMPLE" | "FUNCTIONAL" | "EDGE_CASE";

export interface TestCaseAdmin {
  id: string;
  question_id: string;
  input_data: string;
  expected_output: string;
  explanation?: string | null;
  marks: number;
  display_order: number;
  is_hidden: boolean;
  category?: TestCaseCategory;
}

export interface TestCasePublic {
  id: string;
  input_data: string;
  expected_output: string;
  explanation?: string | null;
  marks: number;
  display_order: number;
  category?: TestCaseCategory;
}

export interface QuestionAdmin {
  id: string;
  assessment_id?: string | null;
  title: string;
  problem_description: string;
  input_format?: string | null;
  output_format?: string | null;
  constraints?: string | null;
  difficulty: DifficultyLevel;
  topic: string;
  marks: number;
  time_limit_seconds: number;
  memory_limit_mb: number;
  display_order: number;
  tags?: string | null;
  starter_code?: string | null;
  is_archived: boolean;
  created_by?: string | null;
  test_cases: TestCaseAdmin[];
  total_attempts?: number;
  solved_count?: number;
  success_rate?: number;
  created_at: string;
  updated_at: string;
}

export interface QuestionPublic {
  id: string;
  title: string;
  problem_description: string;
  input_format?: string | null;
  output_format?: string | null;
  constraints?: string | null;
  difficulty: DifficultyLevel;
  topic: string;
  marks: number;
  time_limit_seconds: number;
  memory_limit_mb: number;
  display_order: number;
  tags?: string | null;
  starter_code?: string | null;
  sample_test_cases: TestCasePublic[];
}

export interface QuestionCreatePayload {
  title: string;
  problem_description: string;
  input_format?: string;
  output_format?: string;
  constraints?: string;
  difficulty: DifficultyLevel;
  topic: string;
  marks: number;
  time_limit_seconds: number;
  memory_limit_mb: number;
  display_order: number;
  tags?: string;
  starter_code?: string;
  assessment_id?: string | null;
  test_cases: Array<{
    input_data: string;
    expected_output: string;
    explanation?: string;
    marks: number;
    display_order: number;
    is_hidden: boolean;
    category?: TestCaseCategory;
  }>;
}

export interface QuestionValidationResponse {
  question_id: string;
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  sample_test_count: number;
  functional_test_count: number;
  edge_test_count: number;
  total_test_marks: number;
  question_marks: number;
}

export interface AssessmentAdmin {
  id: string;
  title: string;
  description?: string | null;
  instructions?: string | null;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  difficulty: DifficultyLevel;
  allowed_languages: string;
  status: AssessmentStatus;
  created_by: string;
  start_time?: string | null;
  end_time?: string | null;
  questions: QuestionAdmin[];
  candidate_count: number;
  proctoring_config?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface AssessmentPublic {
  id: string;
  title: string;
  description?: string | null;
  instructions?: string | null;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  difficulty: DifficultyLevel;
  status: AssessmentStatus;
  allowed_languages: string[];
  start_time?: string | null;
  end_time?: string | null;
  question_count: number;
  has_attempted: boolean;
  attempt_status?: string | null;
  proctoring_config?: Record<string, unknown> | null;
}

export interface AssessmentCreatePayload {
  title: string;
  description?: string;
  instructions?: string;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  difficulty: DifficultyLevel;
  allowed_languages: string;
  start_time?: string | null;
  end_time?: string | null;
  question_ids?: string[];
  proctoring_config?: Record<string, unknown> | null;
}

export interface TestCaseResultPublic {
  test_case_id: string;
  status: string;
  is_sample: boolean;
  execution_time?: number | null;
  memory_usage?: number | null;
  marks_awarded: number;
  error_message?: string | null;
  sample_input?: string | null;
  sample_expected?: string | null;
}

export interface StaticFinding {
  code: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | string;
  message: string;
  line_number?: number | null;
  suggestion?: string | null;
}

export interface StaticAnalysis {
  language: string;
  lines_of_code: number;
  cyclomatic_complexity: number;
  max_nesting_depth: number;
  maintainability_score: number;
  findings: StaticFinding[];
}

export interface AIFeedback {
  logical_approach: string;
  readability: string;
  maintainability: string;
  algorithmic_efficiency: string;
  estimated_time_complexity?: string | null;
  estimated_space_complexity?: string | null;
  improvement_suggestions: string[];
}

export interface SubmissionEvaluation {
  id: string;
  submission_id: string;
  static_analysis?: StaticAnalysis | null;
  ai_feedback?: AIFeedback | null;
  ai_provider: string;
  ai_status: string;
  created_at: string;
}

export interface SubmissionResponse {
  id: string;
  user_id: string;
  assessment_id?: string | null;
  question_id: string;
  programming_language_id: string;
  status: string;
  score: number;
  total_test_cases: number;
  passed_test_cases: number;
  execution_time?: number | null;
  memory_usage?: number | null;
  created_at: string;
  test_case_results: TestCaseResultPublic[];
  evaluation?: SubmissionEvaluation | null;
}

export interface AssessmentStartResponse {
  attempt_id: string;
  assessment_id: string;
  title: string;
  instructions?: string | null;
  started_at: string;
  duration_minutes: number;
  remaining_seconds: number;
  status: string;
  allowed_languages: string[];
  questions: QuestionPublic[];
  drafts: Record<string, string>;
}

export interface AssessmentSubmitResponse {
  attempt_id: string;
  assessment_id: string;
  status: string;
  submitted_at: string;
  total_score: number;
  total_possible_marks: number;
  percentage: number;
  is_passed: boolean;
  submissions: SubmissionResponse[];
}

export interface CohortAttemptResult {
  attempt_id: string;
  user_id: string;
  candidate_name: string;
  candidate_email: string;
  status: string;
  started_at: string;
  submitted_at?: string | null;
  total_score: number;
  percentage: number;
  is_passed: boolean;
}
