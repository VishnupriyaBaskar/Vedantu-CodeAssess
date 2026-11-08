r"""
Base AI Provider Interface
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New
"""

from abc import ABC, abstractmethod
from app.services.ai_evaluation.models import AIEvaluationRequest, AIEvaluationResult


class BaseAIProvider(ABC):
    """Abstract interface for qualitative code evaluation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider, e.g. 'mock' or 'gemini-1.5-flash'."""
        pass

    @abstractmethod
    async def evaluate_code(self, request: AIEvaluationRequest) -> AIEvaluationResult:
        """
        Asynchronously evaluates code against problem specifications.
        Must never expose confidential hidden test cases.
        """
        pass
