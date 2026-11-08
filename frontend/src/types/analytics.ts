/**
 * Analytics and Reporting Types
 * Project: Vedantu Online Coding Assessment Platform (Phase 8)
 * Workspace: E:\VedantuCodingPlatform_New
 */

import { DifficultyBreakdownItem, TopicMasteryItem } from "./adaptive";

export interface ScoreBucket {
  range_label: string;
  count: number;
  percentage: number;
}

export interface TopicPerformanceItem {
  topic: string;
  total_questions: number;
  total_attempts: number;
  average_score_pct: number;
}

export interface DifficultyPerformanceItem {
  difficulty: string;
  total_questions: number;
  total_attempts: number;
  average_score_pct: number;
}

export interface InstructorOverviewKPIs {
  total_candidates: number;
  total_assessments: number;
  published_assessments: number;
  completed_attempts: number;
  active_attempts: number;
  average_score_pct: number;
  pass_percentage: number;
  completion_percentage: number;
  total_questions: number;
  total_submissions: number;
}

export interface CandidateSummaryItem {
  candidate_id: string;
  full_name: string;
  email: string;
  attempt_id?: string | null;
  status?: string | null;
  score?: number | null;
  max_score?: number | null;
  score_pct?: number | null;
  passed?: boolean | null;
  started_at?: string | null;
  completed_at?: string | null;
  proctoring_alerts_count: number;
}

export interface AssessmentAnalyticsResponse {
  assessment_id: string;
  title: string;
  passing_score: number;
  total_marks: number;
  total_enrolled: number;
  total_attempts: number;
  completed_attempts: number;
  active_attempts: number;
  average_score: number;
  average_score_pct: number;
  highest_score: number;
  lowest_score: number;
  pass_count: number;
  fail_count: number;
  pass_percentage: number;
  completion_percentage: number;
  score_distribution: ScoreBucket[];
  topic_breakdown: TopicPerformanceItem[];
  difficulty_breakdown: DifficultyPerformanceItem[];
  candidates: CandidateSummaryItem[];
  proctoring_monitored_sessions: number;
  proctoring_total_events: number;
  proctoring_total_alerts: number;
  proctoring_pending_alerts: number;
  proctoring_high_severity_alerts: number;
}

export interface CohortAnalyticsResponse {
  total_candidates: number;
  active_candidates: number;
  completed_attempts: number;
  average_cohort_score_pct: number;
  topic_proficiencies: TopicPerformanceItem[];
  difficulty_proficiencies: DifficultyPerformanceItem[];
  frequently_failed_topics: string[];
  score_distribution: ScoreBucket[];
  top_performers: CandidateSummaryItem[];
  at_risk_candidates: CandidateSummaryItem[];
}

export interface CandidateSubmissionSummaryItem {
  submission_id: string;
  question_id: string;
  question_title: string;
  topic: string;
  difficulty: string;
  language: string;
  status: string;
  execution_time_ms?: number | null;
  memory_kb?: number | null;
  test_cases_passed: number;
  total_test_cases: number;
  score: number;
  max_score: number;
  static_warnings_count: number;
  static_summary?: string | null;
  ai_quality_score?: number | null;
  submitted_at: string;
}

export interface CandidatePerformanceDetailResponse {
  candidate_id: string;
  full_name: string;
  email: string;
  joined_at: string;
  assessments_attempted: number;
  assessments_completed: number;
  average_score_pct: number;
  best_score_pct: number;
  topic_mastery: TopicMasteryItem[];
  strengths: string[];
  weaknesses: string[];
  difficulty_breakdown: Record<string, DifficultyBreakdownItem>;
  submissions: CandidateSubmissionSummaryItem[];
  assessment_attempts: CandidateSummaryItem[];
}

export interface QuestionPerformanceItem {
  question_id: string;
  title: string;
  topic: string;
  difficulty: string;
  marks: number;
  tags?: string | null;
  is_archived: boolean;
  total_attempts: number;
  solved_count: number;
  success_rate: number;
  average_score: number;
  sample_test_count: number;
  functional_test_count: number;
  edge_test_count: number;
  total_test_marks: number;
  created_at: string;
}
