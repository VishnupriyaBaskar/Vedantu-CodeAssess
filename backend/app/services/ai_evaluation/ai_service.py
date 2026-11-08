r"""
AI Evaluation Orchestrator Service
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New
"""

import logging
from typing import Optional

from app.core.config import settings
from app.services.ai_evaluation.base_provider import BaseAIProvider
from app.services.ai_evaluation.gemini_provider import GeminiAIProvider
from app.services.ai_evaluation.mock_provider import MockAIProvider
from app.services.ai_evaluation.models import AIEvaluationRequest, AIEvaluationResult

logger = logging.getLogger("ai_service")


class AIEvaluationService:
    """Orchestrates AI evaluation dispatch across configured providers."""

    def __init__(self, provider: Optional[BaseAIProvider] = None) -> None:
        self._custom_provider = provider

    def _get_provider(self) -> BaseAIProvider:
        if self._custom_provider:
            return self._custom_provider

        provider_type = (settings.AI_PROVIDER or "mock").strip().lower()

        if provider_type == "gemini":
            return GeminiAIProvider(
                api_key=settings.GEMINI_API_KEY,
                model_name=settings.GEMINI_MODEL,
                timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
            )

        return MockAIProvider()

    async def evaluate_code(self, request: AIEvaluationRequest) -> AIEvaluationResult:
        """
        Coordinates qualitative AI code evaluation.
        Enforces confidentiality contracts and graceful failure handling.
        """
        if not settings.AI_EVALUATION_ENABLED:
            return AIEvaluationResult(
                provider_name="disabled",
                status="SKIPPED",
                feedback=None,
                error_message="AI code evaluation is disabled in platform settings.",
            )

        provider = self._get_provider()
        try:
            return await provider.evaluate_code(request)
        except Exception as e:
            logger.exception("AI evaluation provider %s raised unexpected error: %s", provider.provider_name, e)
            return AIEvaluationResult(
                provider_name=provider.provider_name,
                status="FAILED",
                feedback=None,
                error_message=f"Evaluation failed: {str(e)}",
            )


ai_evaluation_service = AIEvaluationService()
