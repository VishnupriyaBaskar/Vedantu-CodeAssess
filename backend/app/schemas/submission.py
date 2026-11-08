r"""
Student Submission, Draft and Evaluation Pydantic Schemas
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.question import QuestionPublicResponse


class CodeDraftSave(BaseModel):
    """Payload to save/autosave code draft for a question."""
    question_id: uuid.UUID
    programming_language_id: uuid.UUID
    source_code: str = Field(..., max_length=65536)


class CodeDraftResponse(BaseModel):
    question_id: uuid.UUID
    programming_language_id: uuid.UUID
    source_code: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionCreate(BaseModel):
    """Payload for submitting code for evaluation."""
    assessment_id: Optional[uuid.UUID] = None
    question_id: uuid.UUID
    programming_language_id: uuid.UUID
    source_code: str = Field(..., min_length=1, max_length=65536)


class TestCaseResultPublic(BaseModel):
    """
    Projected test case outcome visible to candidate.
    Inputs and expected outputs are included ONLY for sample test cases.
    """
    test_case_id: uuid.UUID
    status: str
    is_sample: bool
    execution_time: Optional[float] = None
    memory_usage: Optional[int] = None
    marks_awarded: float = 0.0
    error_message: Optional[str] = None
    sample_input: Optional[str] = None
    sample_expected: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StaticFindingResponse(BaseModel):
    code: str
    severity: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


class StaticAnalysisResponse(BaseModel):
    language: str = "Unknown"
    lines_of_code: int = 1
    cyclomatic_complexity: int = 1
    max_nesting_depth: int = 1
    maintainability_score: float = 100.0
    findings: List[StaticFindingResponse] = Field(default_factory=list)


class AIFeedbackResponse(BaseModel):
    logical_approach: str
    readability: str
    maintainability: str
    algorithmic_efficiency: str
    estimated_time_complexity: Optional[str] = None
    estimated_space_complexity: Optional[str] = None
    improvement_suggestions: List[str] = Field(default_factory=list)


class SubmissionEvaluationResponse(BaseModel):
    """Full qualitative review (static code analysis + AI feedback)."""
    id: uuid.UUID
    submission_id: uuid.UUID
    static_analysis: Optional[StaticAnalysisResponse] = None
    ai_feedback: Optional[AIFeedbackResponse] = None
    ai_provider: str
    ai_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionResponse(BaseModel):
    """
    Full submission evaluation result returned to student.
    Guarantees confidential hidden test-case contents are never leaked.
    """
    id: uuid.UUID
    user_id: uuid.UUID
    assessment_id: Optional[uuid.UUID] = None
    question_id: uuid.UUID
    programming_language_id: uuid.UUID
    status: str
    score: float
    total_test_cases: int
    passed_test_cases: int
    execution_time: Optional[float] = None
    memory_usage: Optional[int] = None
    created_at: datetime
    test_case_results: List[TestCaseResultPublic] = Field(default_factory=list)
    evaluation: Optional[SubmissionEvaluationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentStartResponse(BaseModel):
    """
    Response returned when an authorized student begins or resumes an assessment.
    """
    attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    title: str
    instructions: Optional[str] = None
    started_at: datetime
    duration_minutes: int
    remaining_seconds: int
    status: str
    allowed_languages: List[str] = Field(default_factory=list)
    questions: List[QuestionPublicResponse] = Field(default_factory=list)
    drafts: Dict[str, str] = Field(default_factory=dict, description="Saved draft code keyed by question_id string")
    proctoring_config: Optional[Dict[str, Any]] = None


class AssessmentSubmitResponse(BaseModel):
    """
    Summary returned upon candidate final assessment submission.
    """
    attempt_id: uuid.UUID
    assessment_id: uuid.UUID
    status: str
    submitted_at: datetime
    total_score: float
    total_possible_marks: int
    percentage: float
    is_passed: bool
    submissions: List[SubmissionResponse] = Field(default_factory=list)
