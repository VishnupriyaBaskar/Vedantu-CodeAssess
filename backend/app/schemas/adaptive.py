r"""
Adaptive Assessment Engine Schemas
Project: Vedantu Online Coding Assessment Platform (Phase 6)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DifficultyBreakdownItem(BaseModel):
    attempted: int = 0
    solved: int = 0
    success_rate: float = 0.0


class TopicMasteryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic: str
    mastery_score: float = Field(..., ge=0.0, le=100.0)
    mastery_level: str  # BEGINNER, DEVELOPING, PROFICIENT, ADVANCED
    confidence_level: str  # LOW, MEDIUM, HIGH
    questions_attempted: int = 0
    questions_solved: int = 0
    total_submissions: int = 0
    successful_submissions: int = 0
    success_rate: float = Field(..., ge=0.0, le=100.0)
    best_score: float = 0.0
    recommended_difficulty: str = "EASY"
    trend: str = "STABLE"  # IMPROVING, STABLE, DECLINING
    last_calculated_at: Optional[datetime] = None


class TopicMasteryListResponse(BaseModel):
    topics: List[TopicMasteryItem]
    overall_mastery_score: float
    overall_mastery_level: str
    overall_recommended_difficulty: str
    total_topics_tracked: int


class StrengthsAndWeaknessesResponse(BaseModel):
    strong_topics: List[TopicMasteryItem]
    needs_improvement_topics: List[TopicMasteryItem]
    improving_topics: List[TopicMasteryItem]
    unattempted_topics: List[str]
    insights_summary: List[str]


class StudentPerformanceResponse(BaseModel):
    total_questions_attempted: int
    total_questions_solved: int
    overall_success_rate: float
    total_submissions: int
    successful_submissions: int
    difficulty_breakdown: Dict[str, DifficultyBreakdownItem]
    assessments_completed: int
    topic_distribution: Dict[str, int]


class QuestionRecommendationItem(BaseModel):
    question_id: uuid.UUID
    title: str
    topic: str
    difficulty: str
    marks: int
    time_limit_seconds: float
    memory_limit_mb: int
    recommendation_reason: str
    target_mastery_level: str


class QuestionRecommendationListResponse(BaseModel):
    recommendations: List[QuestionRecommendationItem]
    student_overall_difficulty: str
    generated_at: datetime


class MasteryHistorySnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    mastery_score: float
    mastery_level: str
    trigger_event: str
    recorded_at: datetime


class MasteryHistoryResponse(BaseModel):
    history: List[MasteryHistorySnapshot]


class PracticeSubmissionRequest(BaseModel):
    programming_language_id: uuid.UUID
    source_code: str


class TopicPracticeQuestionItem(BaseModel):
    id: uuid.UUID
    title: str
    difficulty: str
    marks: int
    time_limit_seconds: float
    memory_limit_mb: int
    sample_test_case_count: int
    is_solved: bool = False
    attempts_count: int = 0
    starter_code: Optional[str] = None


class TopicPracticeDetailResponse(BaseModel):
    topic: str
    description: str
    mastery_score: float
    mastery_level: str
    confidence_level: str
    recommended_difficulty: str
    questions_attempted: int
    questions_solved: int
    total_questions: int
    recommended_question: Optional[TopicPracticeQuestionItem] = None
    questions: List[TopicPracticeQuestionItem]


class TopicCatalogItem(BaseModel):
    topic: str
    description: str
    question_count: int
    questions_solved: int
    questions_attempted: int
    mastery_score: float
    mastery_level: str
    confidence_level: str
    recommended_difficulty: str


class TopicCatalogResponse(BaseModel):
    topics: List[TopicCatalogItem]

