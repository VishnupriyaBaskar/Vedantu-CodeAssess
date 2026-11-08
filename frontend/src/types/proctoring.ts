/**
 * Proctoring and Assessment Integrity TypeScript Definitions
 * Project: Vedantu Online Coding Assessment Platform (Phase 7)
 * Workspace: E:\VedantuCodingPlatform_New
 */

export interface ProctoringConfig {
  enable_webcam: boolean;
  require_fullscreen: boolean;
  enable_tab_monitoring: boolean;
  enable_focus_monitoring: boolean;
  max_tab_switches_warning: number;
  max_tab_switches_alert: number;
  max_blur_seconds_alert: number;
  max_fullscreen_exits_alert: number;
}

export interface ProctoringSessionStartResponse {
  session_id: string;
  assessment_id: string;
  attempt_id: string;
  status: string;
  consent_given: boolean;
  consent_required: boolean;
  monitoring_config: ProctoringConfig;
  privacy_notice: string;
}

export interface ProctoringSessionStatusResponse {
  session_id: string;
  assessment_id: string;
  attempt_id: string;
  status: string;
  consent_given: boolean;
  monitoring_config: ProctoringConfig;
  total_events: number;
  alert_count: number;
  is_active: boolean;
}

export interface ProctoringEventPayload {
  event_type: string;
  severity?: "LOW" | "MEDIUM" | "HIGH";
  event_metadata?: Record<string, unknown>;
  recorded_at?: string;
}

export interface ProctoringEventResponse {
  id: string;
  proctoring_session_id: string;
  assessment_attempt_id: string;
  assessment_id: string;
  user_id: string;
  event_type: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  event_metadata?: Record<string, unknown> | null;
  recorded_at: string;
  created_at: string;
}

export interface ProctoringAlertResponse {
  id: string;
  proctoring_session_id: string;
  assessment_attempt_id: string;
  assessment_id: string;
  user_id: string;
  alert_category: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  explanation: string;
  related_event_ids?: { event_ids?: string[] } | null;
  review_status: "PENDING" | "REVIEWED" | "CLEARED" | "ESCALATED";
  reviewed_by?: string | null;
  reviewer_name?: string | null;
  review_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface CandidateProctoringSummary {
  user_id: string;
  full_name: string;
  email: string;
  attempt_id: string;
  attempt_status: string;
  session_id?: string | null;
  session_status?: string | null;
  consent_given: boolean;
  total_events: number;
  tab_switch_count: number;
  fullscreen_exit_count: number;
  window_blur_count: number;
  total_alerts: number;
  high_severity_alerts: number;
  review_status: string;
  last_heartbeat_at?: string | null;
}

export interface AssessmentProctoringOverviewResponse {
  assessment_id: string;
  title: string;
  total_candidates: number;
  monitored_sessions: number;
  flagged_candidates: number;
  total_alerts: number;
  high_severity_alerts: number;
  monitoring_config: ProctoringConfig;
  candidates: CandidateProctoringSummary[];
}

export interface AttemptProctoringReportResponse {
  attempt_id: string;
  assessment_id: string;
  user_id: string;
  candidate_name: string;
  candidate_email: string;
  session_id?: string | null;
  session_status?: string | null;
  consent_given: boolean;
  consent_timestamp?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  monitoring_config: ProctoringConfig;
  event_summary: Record<string, number>;
  alerts: ProctoringAlertResponse[];
  events: ProctoringEventResponse[];
}

export interface AlertReviewPayload {
  review_status: "PENDING" | "REVIEWED" | "CLEARED" | "ESCALATED";
  review_notes?: string;
}
