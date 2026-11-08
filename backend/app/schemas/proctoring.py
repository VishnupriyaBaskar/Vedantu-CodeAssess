r"""
Proctoring Domain Pydantic Schemas
Project: Vedantu Online Coding Assessment Platform (Phase 7)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


DEFAULT_PROCTORING_CONFIG: Dict[str, Any] = {
    "enable_webcam": False,
    "require_fullscreen": True,
    "enable_tab_monitoring": True,
    "enable_focus_monitoring": True,
    "max_tab_switches_warning": 2,
    "max_tab_switches_alert": 4,
    "max_blur_seconds_alert": 60,
    "max_fullscreen_exits_alert": 3,
}

PRIVACY_DISCLOSURE_TEXT = (
    "Vedantu CodeAssess assessment integrity monitoring: During this examination, "
    "your browser focus, tab switches, and fullscreen state will be logged for integrity validation. "
    "If webcam monitoring is enabled, a live local video indicator will be shown. "
    "No facial recognition, emotion analysis, or automated biometric inferences are performed, "
    "and video is never stored by default. All suspicious activity signals serve strictly as advisory "
    "information for instructor review, never automatic disqualification."
)


class ProctoringConfigSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enable_webcam: bool = Field(default=False, description="Enable optional local webcam presence indicator")
    require_fullscreen: bool = Field(default=True, description="Prompt candidate to enter and maintain fullscreen")
    enable_tab_monitoring: bool = Field(default=True, description="Log tab switches and browser visibility changes")
    enable_focus_monitoring: bool = Field(default=True, description="Log window blur and focus loss events")
    max_tab_switches_warning: int = Field(default=2, ge=1, le=50)
    max_tab_switches_alert: int = Field(default=4, ge=1, le=50)
    max_blur_seconds_alert: int = Field(default=60, ge=5, le=3600)
    max_fullscreen_exits_alert: int = Field(default=3, ge=1, le=50)


class ProctoringSessionStartRequest(BaseModel):
    assessment_id: uuid.UUID
    attempt_id: uuid.UUID


class ProctoringSessionConsentRequest(BaseModel):
    consent: bool = Field(..., description="Candidate explicitly confirms understanding and consent")


class ProctoringEventCreate(BaseModel):
    event_type: str = Field(..., max_length=50, description="Category of event (e.g. TAB_SWITCH, WINDOW_BLUR)")
    severity: str = Field(default="LOW", max_length=20, description="LOW, MEDIUM, or HIGH")
    event_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Contextual metadata (e.g. blur duration)")
    recorded_at: Optional[datetime] = Field(default=None, description="Candidate-side event timestamp")


class ProctoringBatchEventsRequest(BaseModel):
    events: List[ProctoringEventCreate] = Field(..., max_length=100)


class ProctoringHeartbeatRequest(BaseModel):
    client_timestamp: Optional[datetime] = None
    status: Optional[str] = "ACTIVE"


class ProctoringSessionStartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    assessment_id: uuid.UUID
    attempt_id: uuid.UUID
    status: str
    consent_given: bool
    consent_required: bool
    monitoring_config: Dict[str, Any]
    privacy_notice: str


class ProctoringSessionStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    assessment_id: uuid.UUID
    attempt_id: uuid.UUID
    status: str
    consent_given: bool
    monitoring_config: Dict[str, Any]
    total_events: int
    alert_count: int
    is_active: bool


class ProctoringEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proctoring_session_id: uuid.UUID
    assessment_attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    user_id: uuid.UUID
    event_type: str
    severity: str
    event_metadata: Optional[Dict[str, Any]] = None
    recorded_at: datetime
    created_at: datetime


class ProctoringAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proctoring_session_id: uuid.UUID
    assessment_attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    user_id: uuid.UUID
    alert_category: str
    severity: str
    explanation: str
    related_event_ids: Optional[Any] = None
    review_status: str
    reviewed_by: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None


class ProctoringAlertReviewRequest(BaseModel):
    review_status: str = Field(..., description="PENDING, REVIEWED, CLEARED, or ESCALATED")
    review_notes: Optional[str] = Field(default=None, max_length=2000)


class CandidateProctoringSummary(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    attempt_id: uuid.UUID
    attempt_status: str
    session_id: Optional[uuid.UUID] = None
    session_status: Optional[str] = None
    consent_given: bool
    total_events: int
    tab_switch_count: int
    fullscreen_exit_count: int
    window_blur_count: int
    total_alerts: int
    high_severity_alerts: int
    review_status: str
    last_heartbeat_at: Optional[datetime] = None


class AssessmentProctoringOverviewResponse(BaseModel):
    assessment_id: uuid.UUID
    title: str
    total_candidates: int
    monitored_sessions: int
    flagged_candidates: int
    total_alerts: int
    high_severity_alerts: int
    monitoring_config: Dict[str, Any]
    candidates: List[CandidateProctoringSummary]


class AttemptProctoringReportResponse(BaseModel):
    attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    user_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    session_id: Optional[uuid.UUID] = None
    session_status: Optional[str] = None
    consent_given: bool
    consent_timestamp: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    monitoring_config: Dict[str, Any]
    event_summary: Dict[str, int]
    alerts: List[ProctoringAlertResponse]
    events: List[ProctoringEventResponse]
