r"""
Deterministic Mock AI Provider
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New

Provides realistic, zero-cost, offline qualitative code evaluations
based on deterministic pattern analysis of student source code.
"""

import re
from typing import List
from app.services.ai_evaluation.base_provider import BaseAIProvider
from app.services.ai_evaluation.models import (
    AIEvaluationFeedback,
    AIEvaluationRequest,
    AIEvaluationResult,
)


class MockAIProvider(BaseAIProvider):
    """Deterministic, zero-cost offline AI code evaluation provider."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def evaluate_code(self, request: AIEvaluationRequest) -> AIEvaluationResult:
        code = request.source_code
        lang = request.language_name.lower()
        passed_ratio = (
            request.passed_test_cases / request.total_test_cases
            if request.total_test_cases > 0
            else 0.0
        )

        # Detect pattern in code
        has_hashmap = bool(
            re.search(r"dict\(|\{|\bHashMap\b|\bHashSet\b|\.get\(", code)
        )
        has_sort = bool(re.search(r"\.sort\(|sorted\(|Arrays\.sort|Collections\.sort", code))
        has_recursion = bool(re.search(r"def\s+([a-zA-Z0-9_]+)\b.*\1\(", code)) or bool(
            re.search(r"([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{.*\1\(", code, re.DOTALL)
        )
        has_nested_loops = bool(
            re.search(r"(for|while).*(for|while)", code, re.DOTALL)
        )
        has_binary_search = bool(
            re.search(r"\blow\b.*\bhigh\b|\bleft\b.*\bright\b|\bmid\b", code)
        )

        # 1. Determine Logical Approach
        if has_binary_search:
            approach = "Binary search / divide-and-conquer pattern reducing the search space logarithmically."
            time_comp = "O(log N)"
            space_comp = "O(1)"
        elif has_nested_loops:
            approach = "Exhaustive / multi-pass search using nested iteration across candidate elements."
            time_comp = "O(N^2)"
            space_comp = "O(1)"
        elif has_sort:
            approach = "Sorting-based preprocessing followed by linear sweep."
            time_comp = "O(N log N)"
            space_comp = "O(N)" if "python" in lang else "O(log N)"
        elif has_hashmap:
            approach = "Hash-indexed frequency lookup optimizing member lookups to amortized constant time."
            time_comp = "O(N)"
            space_comp = "O(N)"
        elif has_recursion:
            approach = "Recursive state decomposition resolving sub-problems via the call stack."
            time_comp = "O(2^N)" if "return" in code else "O(N)"
            space_comp = "O(N) recursion stack"
        else:
            approach = "Single-pass linear scan processing inputs sequentially."
            time_comp = "O(N)"
            space_comp = "O(1)"

        # 2. Readability Analysis
        lines = [line.strip() for line in code.splitlines() if line.strip()]
        avg_line_len = sum(len(l) for l in lines) / max(1, len(lines))
        has_comments = bool(re.search(r"#|//|/\*", code))

        if avg_line_len < 70 and has_comments:
            readability = (
                "Clean, readable structure with appropriate line lengths and informative inline comments. "
                "Identifiers communicate clear intent."
            )
        elif avg_line_len < 80:
            readability = (
                "Adequate code readability and structural flow. "
                "Adding brief inline comments for critical edge conditions would further improve clarity."
            )
        else:
            readability = (
                "Densely packed statements with long expressions. "
                "Breaking long expressions into well-named temporary variables will improve cognitive readability."
            )

        # 3. Maintainability Analysis
        if has_nested_loops:
            maintainability = (
                "Moderate maintainability due to nested flow control. "
                "Decomposing inner loops into helper functions would isolate responsibilities and improve testability."
            )
        else:
            maintainability = (
                "High maintainability with modular control flow and predictable execution boundaries."
            )

        # 4. Algorithmic Efficiency Description
        if passed_ratio == 1.0:
            efficiency = (
                f"Optimal execution within problem resource limits. Estimated asymptotic runtime is {time_comp} "
                f"with {space_comp} auxiliary memory."
            )
        elif request.execution_status == "TIME_LIMIT_EXCEEDED":
            efficiency = (
                f"Suboptimal runtime efficiency resulting in Time Limit Exceeded. The current approach exhibits {time_comp} "
                "complexity; consider an indexed lookup (hash table) or two-pointer technique to reduce execution time."
            )
        else:
            efficiency = (
                f"Estimated algorithmic complexity is {time_comp} time and {space_comp} space. "
                "Review edge cases and boundaries to ensure full correctness across all input ranges."
            )

        # 5. Improvement Suggestions
        suggestions: List[str] = []
        if has_nested_loops:
            suggestions.append(
                "Consider replacing the nested loop with a hash table or two-pointer scan to achieve O(N) linear time."
            )
        if not has_comments:
            suggestions.append(
                "Add concise inline documentation explaining the problem invariant and non-obvious branching logic."
            )
        if "python" in lang and not re.search(r":\s*[a-zA-Z\[\],]+", code):
            suggestions.append(
                "Consider adding Python type annotations (PEP 484) to function signatures to clarify input and return expectations."
            )
        if "java" in lang and "Scanner" in code:
            suggestions.append(
                "For high-volume competitive I/O in Java, consider BufferedReader and StringTokenizer instead of Scanner."
            )
        if passed_ratio < 1.0:
            suggestions.append(
                "Verify edge boundaries: check empty collections, single-element collections, extreme min/max values, and duplicate elements."
            )
        else:
            suggestions.append(
                "Ensure defensive boundary validation is performed on inputs before main algorithmic execution."
            )

        feedback = AIEvaluationFeedback(
            logical_approach=approach,
            readability=readability,
            maintainability=maintainability,
            algorithmic_efficiency=efficiency,
            estimated_time_complexity=time_comp,
            estimated_space_complexity=space_comp,
            improvement_suggestions=suggestions[:4],
        )

        return AIEvaluationResult(
            provider_name=self.provider_name,
            status="COMPLETED",
            feedback=feedback,
            error_message=None,
        )
