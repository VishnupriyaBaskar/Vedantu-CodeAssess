r"""
Question Bank and TestCase Pydantic Schemas
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TestCaseBase(BaseModel):
    input_data: str = Field(..., description="Standard input provided to student program")
    expected_output: str = Field(..., description="Expected standard output to match")
    explanation: Optional[str] = Field(None, description="Optional educational explanation for sample test cases")
    marks: int = Field(default=5, ge=0, description="Marks allocated to this test case")
    display_order: int = Field(default=1, ge=1)
    is_hidden: bool = Field(default=True, description="True for private evaluation tests, False for public sample cases")
    category: str = Field(default="FUNCTIONAL", description="SAMPLE, FUNCTIONAL, or EDGE_CASE")


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    explanation: Optional[str] = None
    marks: Optional[int] = Field(None, ge=0)
    display_order: Optional[int] = Field(None, ge=1)
    is_hidden: Optional[bool] = None
    category: Optional[str] = None


class TestCasePublicResponse(BaseModel):
    """
    Public test case model for student consumers.
    Guarantees hidden test case inputs and expected outputs are NEVER returned.
    """
    id: uuid.UUID
    input_data: str
    expected_output: str
    explanation: Optional[str] = None
    marks: int
    display_order: int
    category: str = "SAMPLE"

    model_config = ConfigDict(from_attributes=True)


class TestCaseAdminResponse(TestCaseBase):
    """
    Administrative test case model for authoring instructors.
    """
    id: uuid.UUID
    question_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class QuestionBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    problem_description: str = Field(..., min_length=5)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    difficulty: str = Field(default="MEDIUM", pattern="^(EASY|MEDIUM|HARD)$")
    topic: str = Field(default="General", max_length=100)
    marks: int = Field(default=10, ge=1)
    time_limit_seconds: float = Field(default=2.0, ge=0.1, le=15.0)
    memory_limit_mb: int = Field(default=256, ge=16, le=1024)
    display_order: int = Field(default=1, ge=1)
    tags: Optional[str] = Field(default=None, max_length=255, description="Comma-separated tags")
    starter_code: Optional[str] = Field(default=None, description="Optional starter code template")


class QuestionCreate(QuestionBase):
    assessment_id: Optional[uuid.UUID] = Field(None, description="Optional association to an existing assessment")
    test_cases: List[TestCaseCreate] = Field(default_factory=list, description="Initial set of sample and hidden test cases")


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    problem_description: Optional[str] = Field(None, min_length=5)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(EASY|MEDIUM|HARD)$")
    topic: Optional[str] = Field(None, max_length=100)
    marks: Optional[int] = Field(None, ge=1)
    time_limit_seconds: Optional[float] = Field(None, ge=0.1, le=15.0)
    memory_limit_mb: Optional[int] = Field(None, ge=16, le=1024)
    display_order: Optional[int] = Field(None, ge=1)
    tags: Optional[str] = None
    starter_code: Optional[str] = None
    is_archived: Optional[bool] = None
    assessment_id: Optional[uuid.UUID] = None


class QuestionPublicResponse(BaseModel):
    """
    Student-facing question schema.
    Strictly isolated: returns ONLY public sample test cases. Hidden test cases are completely omitted.
    """
    id: uuid.UUID
    title: str
    problem_description: str
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    difficulty: str
    topic: str
    marks: int
    time_limit_seconds: float
    memory_limit_mb: int
    display_order: int
    tags: Optional[str] = None
    starter_code: Optional[str] = None
    sample_test_cases: List[TestCasePublicResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class QuestionAdminResponse(QuestionBase):
    """
    Instructor/Admin question management schema with full test case suite, archive status, and quality indicators.
    """
    id: uuid.UUID
    assessment_id: Optional[uuid.UUID] = None
    is_archived: bool
    created_by: Optional[uuid.UUID] = None
    test_cases: List[TestCaseAdminResponse] = Field(default_factory=list)
    total_attempts: int = 0
    solved_count: int = 0
    success_rate: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionValidationResponse(BaseModel):
    """Result of question publishing validation."""
    question_id: uuid.UUID
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    sample_test_count: int = 0
    functional_test_count: int = 0
    edge_test_count: int = 0
    total_test_marks: int = 0
    question_marks: int = 0
