import { QuestionPublic, SubmissionResponse } from "./assessment";

export interface DifficultyBreakdownItem {
  attempted: number;
  solved: number;
  success_rate: number;
}

export interface TopicMasteryItem {
  topic: string;
  mastery_score: number;
  mastery_level: "BEGINNER" | "DEVELOPING" | "PROFICIENT" | "ADVANCED";
  confidence_level: "LOW" | "MEDIUM" | "HIGH";
  questions_attempted: number;
  questions_solved: number;
  total_submissions: number;
  successful_submissions: number;
  success_rate: number;
  best_score: number;
  recommended_difficulty: "EASY" | "MEDIUM" | "HARD";
  trend: "IMPROVING" | "STABLE" | "DECLINING";
  last_calculated_at?: string;
}

export interface TopicMasteryListResponse {
  topics: TopicMasteryItem[];
  overall_mastery_score: number;
  overall_mastery_level: "BEGINNER" | "DEVELOPING" | "PROFICIENT" | "ADVANCED";
  overall_recommended_difficulty: "EASY" | "MEDIUM" | "HARD";
  total_topics_tracked: number;
}

export interface StrengthsAndWeaknessesResponse {
  strong_topics: TopicMasteryItem[];
  needs_improvement_topics: TopicMasteryItem[];
  improving_topics: TopicMasteryItem[];
  unattempted_topics: string[];
  insights_summary: string[];
}

export interface StudentPerformanceResponse {
  total_questions_attempted: number;
  total_questions_solved: number;
  overall_success_rate: number;
  total_submissions: number;
  successful_submissions: number;
  difficulty_breakdown: Record<string, DifficultyBreakdownItem>;
  assessments_completed: number;
  topic_distribution: Record<string, number>;
}

export interface QuestionRecommendationItem {
  question_id: string;
  title: string;
  topic: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  marks: number;
  time_limit_seconds: number;
  memory_limit_mb: number;
  recommendation_reason: string;
  target_mastery_level: string;
}

export interface QuestionRecommendationListResponse {
  recommendations: QuestionRecommendationItem[];
  student_overall_difficulty: "EASY" | "MEDIUM" | "HARD";
  generated_at: string;
}

export interface MasteryHistorySnapshot {
  id: string;
  topic: string;
  mastery_score: number;
  mastery_level: string;
  trigger_event: string;
  recorded_at: string;
}

export interface MasteryHistoryResponse {
  history: MasteryHistorySnapshot[];
}

export interface PracticeSubmissionRequest {
  programming_language_id: string;
  source_code: string;
}

export interface TopicPracticeQuestionItem {
  id: string;
  title: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  marks: number;
  time_limit_seconds: number;
  memory_limit_mb: number;
  sample_test_case_count: number;
  is_solved: boolean;
  attempts_count: number;
  starter_code?: string;
}

export interface TopicPracticeDetailResponse {
  topic: string;
  description: string;
  mastery_score: number;
  mastery_level: string;
  confidence_level: string;
  recommended_difficulty: string;
  questions_attempted: number;
  questions_solved: number;
  total_questions: number;
  recommended_question?: TopicPracticeQuestionItem | null;
  questions: TopicPracticeQuestionItem[];
}

export interface TopicCatalogItem {
  topic: string;
  description: string;
  question_count: number;
  questions_solved: number;
  questions_attempted: number;
  mastery_score: number;
  mastery_level: string;
  confidence_level: string;
  recommended_difficulty: string;
}

export interface TopicCatalogResponse {
  topics: TopicCatalogItem[];
}

