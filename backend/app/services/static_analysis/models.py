r"""
Static Code Analysis Data Models
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class StaticFinding(BaseModel):
    """Individual code smell, convention warning or complexity finding."""
    code: str = Field(..., description="Machine-readable rule identifier, e.g. PY_BARE_EXCEPT")
    severity: str = Field(..., description="INFO, WARNING, or ERROR")
    message: str = Field(..., description="Human-readable explanation of the issue")
    line_number: Optional[int] = Field(None, description="Line number where issue was detected, if available")
    suggestion: Optional[str] = Field(None, description="Actionable recommendation to fix the issue")


class StaticAnalysisResult(BaseModel):
    """Aggregate static analysis report generated without executing student code."""
    language: str
    lines_of_code: int
    cyclomatic_complexity: int
    max_nesting_depth: int
    maintainability_score: float = Field(..., ge=0.0, le=100.0)
    findings: List[StaticFinding] = Field(default_factory=list)
