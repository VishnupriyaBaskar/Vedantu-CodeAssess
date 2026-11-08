r"""
Google Gemini AI Code Evaluation Provider
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New

Integrates with Google Gemini API for qualitative code review.
CONFIDENTIALITY ENFORCEMENT: Never sends hidden test-case inputs or expected outputs.
"""

import json
import logging
import re
from typing import Optional
import httpx

from app.services.ai_evaluation.base_provider import BaseAIProvider
from app.services.ai_evaluation.models import (
    AIEvaluationFeedback,
    AIEvaluationRequest,
    AIEvaluationResult,
)

logger = logging.getLogger("gemini_provider")


class GeminiAIProvider(BaseAIProvider):
    """
    Evaluates candidate code using Google's Gemini models via official REST API.
    Activated only when GEMINI_API_KEY is configured.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return self.model_name

    async def evaluate_code(self, request: AIEvaluationRequest) -> AIEvaluationResult:
        if not self.api_key:
            return AIEvaluationResult(
                provider_name=self.provider_name,
                status="UNAVAILABLE",
                feedback=None,
                error_message="Gemini API key is not configured.",
            )

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )

        prompt = f"""You are a senior technical interviewer and competitive programming coach at Vedantu.
Review the following code submission objectively.
Problem: {request.problem_title}
Description: {request.problem_description}
Constraints: {request.constraints or 'Standard competition constraints'}
Language: {request.language_name}
Automated Execution Status: {request.execution_status} (Passed {request.passed_test_cases}/{request.total_test_cases} test cases, Score: {request.score})

Source Code:
```{request.language_name.lower()}
{request.source_code}
```

Return ONLY a valid JSON object matching the following structure with no markdown code fences:
{{
  "logical_approach": "concise description of the algorithmic approach used",
  "readability": "concise assessment of readability, naming and structure",
  "maintainability": "concise assessment of code maintainability and modularity",
  "algorithmic_efficiency": "concise assessment of time and space complexity",
  "estimated_time_complexity": "e.g. O(N), O(N^2), O(N log N)",
  "estimated_space_complexity": "e.g. O(1), O(N)",
  "improvement_suggestions": [
    "actionable tip 1",
    "actionable tip 2",
    "actionable tip 3"
  ]
}}
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)

            if response.status_code != 200:
                logger.warning(
                    "Gemini API returned status %d: %s",
                    response.status_code,
                    response.text,
                )
                return AIEvaluationResult(
                    provider_name=self.provider_name,
                    status="FAILED",
                    feedback=None,
                    error_message=f"Gemini API error (HTTP {response.status_code}).",
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return AIEvaluationResult(
                    provider_name=self.provider_name,
                    status="FAILED",
                    feedback=None,
                    error_message="Gemini returned no response candidates.",
                )

            part_text = (
                candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            )
            clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", part_text.strip())

            parsed = json.loads(clean_text)
            feedback = AIEvaluationFeedback(
                logical_approach=str(parsed.get("logical_approach", "Standard algorithmic approach.")),
                readability=str(parsed.get("readability", "Readable structure.")),
                maintainability=str(parsed.get("maintainability", "Maintainable implementation.")),
                algorithmic_efficiency=str(parsed.get("algorithmic_efficiency", "Standard complexity.")),
                estimated_time_complexity=parsed.get("estimated_time_complexity"),
                estimated_space_complexity=parsed.get("estimated_space_complexity"),
                improvement_suggestions=[str(s) for s in parsed.get("improvement_suggestions", [])],
            )

            return AIEvaluationResult(
                provider_name=self.provider_name,
                status="COMPLETED",
                feedback=feedback,
                error_message=None,
            )

        except httpx.TimeoutException:
            logger.warning("Gemini evaluation timed out after %ss", self.timeout_seconds)
            return AIEvaluationResult(
                provider_name=self.provider_name,
                status="FAILED",
                feedback=None,
                error_message="Gemini API request timed out.",
            )
        except Exception as e:
            logger.exception("Gemini evaluation failed unexpectedly: %s", e)
            return AIEvaluationResult(
                provider_name=self.provider_name,
                status="FAILED",
                feedback=None,
                error_message=f"Gemini evaluation error: {str(e)}",
            )
