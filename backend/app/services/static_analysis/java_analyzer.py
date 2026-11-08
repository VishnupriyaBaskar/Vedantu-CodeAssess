r"""
Java Lightweight Lexical and Structural Static Code Analyzer
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New

Safely inspects student Java code using lexical token and structural regex analysis.
NEVER executes untrusted code.
"""

import re
from typing import List
from app.services.static_analysis.models import StaticAnalysisResult, StaticFinding

# Regex patterns for Java structural analysis
_CLASS_PATTERN = re.compile(r"\b(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:class|interface|enum)\s+([A-Za-z0-9_]+)")
_METHOD_PATTERN = re.compile(r"\b(?:public|private|protected|static|final|\s)+\s+[\w<>\[\],\s]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{")
_BRANCH_PATTERN = re.compile(r"\b(if|else\s+if|for|while|case|catch)\b|\?")
_EMPTY_CATCH_PATTERN = re.compile(r"catch\s*\([^)]+\)\s*\{\s*\}")
_REDUNDANT_BOOLEAN_PATTERN = re.compile(r"==\s*true|==\s*false|!=\s*true|!=\s*false")
_SYSTEM_GC_PATTERN = re.compile(r"\bSystem\s*\.\s*gc\s*\(\s*\)")
_PASCAL_CASE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_CAMEL_CASE = re.compile(r"^[a-z][a-zA-Z0-9]*$")


def analyze_java_code(source_code: str) -> StaticAnalysisResult:
    """
    Performs safe static lexical and structural analysis on Java source code.
    Returns metrics, complexity, and structured findings without execution.
    """
    lines = source_code.splitlines()
    loc = len([line for line in lines if line.strip() and not line.strip().startswith("//") and not line.strip().startswith("/*")])

    findings: List[StaticFinding] = []
    complexity = 1
    max_nesting = 0
    current_nesting = 0

    # 1. Line-by-line inspection for nesting, branch complexity, and line-specific smells
    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track block braces (excluding string literals or character literals)
        sanitized_line = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', stripped)
        sanitized_line = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "''", sanitized_line)

        open_braces = sanitized_line.count("{")
        close_braces = sanitized_line.count("}")

        current_nesting += open_braces
        if current_nesting > max_nesting:
            max_nesting = current_nesting
        if current_nesting > 4 and open_braces > 0:
            findings.append(
                StaticFinding(
                    code="JAVA_DEEP_NESTING",
                    severity="WARNING",
                    message=f"Deeply nested code block (nesting level {current_nesting}).",
                    line_number=line_idx,
                    suggestion="Refactor deeply nested blocks into helper methods to improve maintainability.",
                )
            )
        current_nesting = max(0, current_nesting - close_braces)

        # Count branch decision points for cyclomatic complexity
        matches = _BRANCH_PATTERN.findall(sanitized_line)
        complexity += len(matches)

        # Redundant boolean check
        if _REDUNDANT_BOOLEAN_PATTERN.search(sanitized_line):
            findings.append(
                StaticFinding(
                    code="JAVA_REDUNDANT_BOOLEAN",
                    severity="INFO",
                    message="Redundant boolean comparison (e.g. '== true' or '== false').",
                    line_number=line_idx,
                    suggestion="Use direct boolean variable or condition (e.g., 'if (isValid)' instead of 'if (isValid == true)').",
                )
            )

        # System.gc() call
        if _SYSTEM_GC_PATTERN.search(sanitized_line):
            findings.append(
                StaticFinding(
                    code="JAVA_SYSTEM_GC",
                    severity="WARNING",
                    message="Explicit invocation of 'System.gc()' detected.",
                    line_number=line_idx,
                    suggestion="Allow the JVM Garbage Collector to manage memory automatically; avoid explicit System.gc().",
                )
            )

    # 2. Whole-source checks: Empty catch blocks
    for match in _EMPTY_CATCH_PATTERN.finditer(source_code):
        # Approximate line number
        start_pos = match.start()
        line_num = source_code[:start_pos].count("\n") + 1
        findings.append(
            StaticFinding(
                code="JAVA_EMPTY_CATCH",
                severity="WARNING",
                message="Empty catch block found. Exception is swallowed without handling or logging.",
                line_number=line_num,
                suggestion="Log the exception, take corrective action, or rethrow as a domain exception.",
            )
        )

    # 3. Class and Method Naming Conventions
    for match in _CLASS_PATTERN.finditer(source_code):
        class_name = match.group(1)
        start_pos = match.start()
        line_num = source_code[:start_pos].count("\n") + 1
        if not _PASCAL_CASE.match(class_name):
            findings.append(
                StaticFinding(
                    code="JAVA_NAMING_CLASS",
                    severity="INFO",
                    message=f"Class/Interface name '{class_name}' does not follow Java PascalCase convention.",
                    line_number=line_num,
                    suggestion=f"Rename '{class_name}' to start with an uppercase letter.",
                )
            )

    for match in _METHOD_PATTERN.finditer(source_code):
        method_name = match.group(1)
        # Exclude constructor-like names (matching class names) or special keywords
        if method_name in ("main", "toString", "equals", "hashCode"):
            continue
        start_pos = match.start()
        line_num = source_code[:start_pos].count("\n") + 1
        if not _CAMEL_CASE.match(method_name):
            findings.append(
                StaticFinding(
                    code="JAVA_NAMING_METHOD",
                    severity="INFO",
                    message=f"Method name '{method_name}' should follow camelCase naming convention.",
                    line_number=line_num,
                    suggestion=f"Rename '{method_name}' to camelCase format.",
                )
            )

    # 4. Complexity threshold
    if complexity > 10:
        findings.append(
            StaticFinding(
                code="JAVA_HIGH_COMPLEXITY",
                severity="WARNING",
                message=f"High cyclomatic complexity ({complexity}). Solution contains multiple nested branches.",
                line_number=1,
                suggestion="Decompose complex logic into specialized helper methods.",
            )
        )

    # 5. Maintainability Score Calculation
    score = 100.0
    for finding in findings:
        if finding.severity == "ERROR":
            score -= 15.0
        elif finding.severity == "WARNING":
            score -= 5.0
        elif finding.severity == "INFO":
            score -= 2.0

    if complexity > 8:
        score -= min(25.0, (complexity - 8) * 2.0)
    if max_nesting > 4:
        score -= min(20.0, (max_nesting - 4) * 4.0)

    maintainability_score = round(max(0.0, min(100.0, score)), 1)

    return StaticAnalysisResult(
        language="Java",
        lines_of_code=max(1, loc),
        cyclomatic_complexity=complexity,
        max_nesting_depth=max(0, max_nesting),
        maintainability_score=maintainability_score,
        findings=findings,
    )
