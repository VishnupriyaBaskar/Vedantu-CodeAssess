r"""
Static Analysis Dispatcher Service
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New
"""

from app.services.static_analysis.models import StaticAnalysisResult
from app.services.static_analysis.python_analyzer import analyze_python_code
from app.services.static_analysis.java_analyzer import analyze_java_code


def analyze_code(language_name: str, source_code: str) -> StaticAnalysisResult:
    """
    Dispatches source code to the appropriate language static analyzer.
    Guarantees that student code is never executed.
    """
    norm_lang = language_name.strip().lower()

    if "python" in norm_lang:
        return analyze_python_code(source_code)
    elif "java" in norm_lang:
        return analyze_java_code(source_code)
    else:
        # Generic fallback for unsupported languages: basic line counting
        loc = len([line for line in source_code.splitlines() if line.strip()])
        return StaticAnalysisResult(
            language=language_name,
            lines_of_code=max(1, loc),
            cyclomatic_complexity=1,
            max_nesting_depth=1,
            maintainability_score=85.0,
            findings=[],
        )
