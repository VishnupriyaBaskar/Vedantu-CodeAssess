r"""
Analytics & Instructor Reporting Pydantic Schemas
Project: Vedantu Online Coding Assessment Platform (Phase 8)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.adaptive import DifficultyBreakdownItem, TopicMasteryItem


class ScoreBucket(BaseModel):
    range_label: str = Field(..., description="E.g., '0-20%', '21-40%', etc.")
    count: int = 0
    percentage: float = 0.0


class TopicPerformanceItem(BaseModel):
    topic: str
    total_questions: int = 0
    total_attempts: int = 0
    average_score_pct: float = 0.0


class DifficultyPerformanceItem(BaseModel):
    difficulty: str
    total_questions: int = 0
    total_attempts: int = 0
    average_score_pct: float = 0.0


class InstructorOverviewKPIs(BaseModel):
    """
    Live aggregated high-level KPIs for the instructor management dashboard.
    """
    total_candidates: int = Field(default=0, description="Total registered students")
    total_assessments: int = Field(default=0, description="Total created assessments")
    published_assessments: int = Field(default=0, description="Currently published assessments")
    completed_attempts: int = Field(default=0, description="Total completed assessment attempts")
    active_attempts: int = Field(default=0, description="Currently in-progress assessment attempts")
    average_score_pct: float = Field(default=0.0, description="Mean score across all completed attempts")
    pass_percentage: float = Field(default=0.0, description="Percentage of completed attempts meeting passing criteria")
    completion_percentage: float = Field(default=0.0, description="Percentage of started attempts completed")
    total_questions: int = Field(default=0, description="Total questions in question bank")
    total_submissions: int = Field(default=0, description="Total code submissions evaluated")


class CandidateSummaryItem(BaseModel):
    candidate_id: uuid.UUID
    full_name: str
    email: str
    attempt_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    score_pct: Optional[float] = None
    passed: Optional[bool] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    proctoring_alerts_count: int = 0


class AssessmentAnalyticsResponse(BaseModel):
    """
    Comprehensive performance metrics for a specific assessment.
    """
    assessment_id: uuid.UUID
    title: str
    passing_score: int
    total_marks: int
    total_enrolled: int
    total_attempts: int
    completed_attempts: int
    active_attempts: int
    average_score: float
    average_score_pct: float
    highest_score: float
    lowest_score: float
    pass_count: int
    fail_count: int
    pass_percentage: float
    completion_percentage: float
    score_distribution: List[ScoreBucket] = Field(default_factory=list)
    topic_breakdown: List[TopicPerformanceItem] = Field(default_factory=list)
    difficulty_breakdown: List[DifficultyPerformanceItem] = Field(default_factory=list)
    candidates: List[CandidateSummaryItem] = Field(default_factory=list)
    # Integrated Proctoring Metrics (Phase 7 synergy)
    proctoring_monitored_sessions: int = 0
    proctoring_total_events: int = 0
    proctoring_total_alerts: int = 0
    proctoring_pending_alerts: int = 0
    proctoring_high_severity_alerts: int = 0


class CohortAnalyticsResponse(BaseModel):
    """
    Cohort-level comparative analytics across assessments or general student population.
    """
    total_candidates: int
    active_candidates: int
    completed_attempts: int
    average_cohort_score_pct: float
    topic_proficiencies: List[TopicPerformanceItem] = Field(default_factory=list)
    difficulty_proficiencies: List[DifficultyPerformanceItem] = Field(default_factory=list)
    frequently_failed_topics: List[str] = Field(default_factory=list)
    score_distribution: List[ScoreBucket] = Field(default_factory=list)
    top_performers: List[CandidateSummaryItem] = Field(default_factory=list)
    at_risk_candidates: List[CandidateSummaryItem] = Field(default_factory=list)


class CandidateSubmissionSummaryItem(BaseModel):
    submission_id: uuid.UUID
    question_id: uuid.UUID
    question_title: str
    topic: str
    difficulty: str
    language: str
    status: str
    execution_time_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    test_cases_passed: int = 0
    total_test_cases: int = 0
    score: int = 0
    max_score: int = 0
    static_warnings_count: int = 0
    static_summary: Optional[str] = None
    ai_quality_score: Optional[int] = None
    submitted_at: datetime


class CandidatePerformanceDetailResponse(BaseModel):
    """
    Detailed individual candidate performance report.
    Guarantees hidden test case inputs and expected outputs are NEVER returned.
    """
    candidate_id: uuid.UUID
    full_name: str
    email: str
    joined_at: datetime
    assessments_attempted: int
    assessments_completed: int
    average_score_pct: float
    best_score_pct: float
    # Reusing Phase 6 Mastery Models
    topic_mastery: List[TopicMasteryItem] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    difficulty_breakdown: Dict[str, DifficultyBreakdownItem] = Field(default_factory=dict)
    # Submissions
    submissions: List[CandidateSubmissionSummaryItem] = Field(default_factory=list)
    assessment_attempts: List[CandidateSummaryItem] = Field(default_factory=list)


class QuestionPerformanceItem(BaseModel):
    """
    Question Bank quality and analytics metrics.
    """
    question_id: uuid.UUID
    title: str
    topic: str
    difficulty: str
    marks: int
    tags: Optional[str] = None
    is_archived: bool
    total_attempts: int = 0
    solved_count: int = 0
    success_rate: float = 0.0
    average_score: float = 0.0
    sample_test_count: int = 0
    functional_test_count: int = 0
    edge_test_count: int = 0
    total_test_marks: int = 0
    created_at: datetime
