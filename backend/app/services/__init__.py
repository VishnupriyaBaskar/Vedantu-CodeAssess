r"""
Services Package
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New
"""

from app.services.judge0_service import Judge0Service, judge0_service
from app.services.evaluation_service import EvaluationService, evaluation_service
from app.services.static_analysis import StaticAnalysisResult, StaticFinding, analyze_code
from app.services.ai_evaluation import (
    AIEvaluationFeedback,
    AIEvaluationRequest,
    AIEvaluationResult,
    BaseAIProvider,
    MockAIProvider,
    GeminiAIProvider,
    AIEvaluationService,
    ai_evaluation_service,
)
from app.services.adaptive_service import AdaptiveService, adaptive_service
from app.services.proctoring_service import ProctoringService, proctoring_service
from app.services.analytics_service import AnalyticsService, analytics_service

__all__ = [
    "Judge0Service",
    "judge0_service",
    "EvaluationService",
    "evaluation_service",
    "StaticAnalysisResult",
    "StaticFinding",
    "analyze_code",
    "AIEvaluationFeedback",
    "AIEvaluationRequest",
    "AIEvaluationResult",
    "BaseAIProvider",
    "MockAIProvider",
    "GeminiAIProvider",
    "AIEvaluationService",
    "ai_evaluation_service",
    "AdaptiveService",
    "adaptive_service",
    "ProctoringService",
    "proctoring_service",
    "AnalyticsService",
    "analytics_service",
]
