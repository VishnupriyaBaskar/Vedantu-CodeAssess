r"""
AI Evaluation Domain Models & Schemas
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AIEvaluationRequest(BaseModel):
    """
    Context passed to AI evaluation providers.
    CONFIDENTIALITY CONTRACT:
    Hidden test-case inputs and expected outputs must NEVER be included here.
    """
    problem_title: str
    problem_description: str
    constraints: Optional[str] = None
    language_name: str
    source_code: str
    execution_status: str
    score: float
    total_test_cases: int
    passed_test_cases: int


class AIEvaluationFeedback(BaseModel):
    """Structured qualitative evaluation returned by AI providers."""
    logical_approach: str = Field(..., description="Assessment of candidate's algorithmic approach")
    readability: str = Field(..., description="Evaluation of code readability, structure, and naming")
    maintainability: str = Field(..., description="Evaluation of modularity and maintainability")
    algorithmic_efficiency: str = Field(..., description="Time and space complexity analysis and observations")
    estimated_time_complexity: Optional[str] = Field(None, description="e.g. O(N), O(N^2), O(N log N)")
    estimated_space_complexity: Optional[str] = Field(None, description="e.g. O(1), O(N)")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Actionable suggestions for code optimization")


class AIEvaluationResult(BaseModel):
    """Full outcome from an AI evaluation provider."""
    provider_name: str
    status: str = Field(..., description="COMPLETED, FAILED, UNAVAILABLE, or SKIPPED")
    feedback: Optional[AIEvaluationFeedback] = None
    error_message: Optional[str] = None
