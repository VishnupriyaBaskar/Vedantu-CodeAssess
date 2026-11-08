r"""
Python 3 AST-Based Static Code Analyzer
Project: Vedantu Online Coding Assessment Platform (Stage 5)
Workspace: E:\VedantuCodingPlatform_New

Safely inspects student Python code using Python's built-in AST parser.
NEVER executes untrusted code.
"""

import ast
import re
from typing import List, Set
from app.services.static_analysis.models import StaticAnalysisResult, StaticFinding

_SNAKE_CASE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
_PASCAL_CASE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_DUNDER_PATTERN = re.compile(r"^__[a-zA-Z0-9_]+__$")


class _PythonASTVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.complexity = 1
        self.findings: List[StaticFinding] = []
        self.max_nesting_depth = 0
        self.current_depth = 0
        self.assigned_vars: Set[str] = set()

    def _track_depth(self, node: ast.AST) -> None:
        self.current_depth += 1
        if self.current_depth > self.max_nesting_depth:
            self.max_nesting_depth = self.current_depth
        if self.current_depth > 3:
            self.findings.append(
                StaticFinding(
                    code="PY_DEEP_NESTING",
                    severity="WARNING",
                    message=f"Deeply nested code block (nesting depth {self.current_depth}).",
                    line_number=getattr(node, "lineno", None),
                    suggestion="Refactor nested loops or conditionals into smaller helper functions.",
                )
            )

    def _untrack_depth(self) -> None:
        self.current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self._track_depth(node)
        self.generic_visit(node)
        self._untrack_depth()

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self._track_depth(node)
        self.generic_visit(node)
        self._untrack_depth()

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self._track_depth(node)
        self.generic_visit(node)
        self._untrack_depth()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self._track_depth(node)
        self.generic_visit(node)
        self._untrack_depth()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        # Check for bare except:
        if node.type is None:
            self.findings.append(
                StaticFinding(
                    code="PY_BARE_EXCEPT",
                    severity="WARNING",
                    message="Bare 'except:' clause caught without specifying exception type.",
                    line_number=getattr(node, "lineno", None),
                    suggestion="Catch specific exceptions like 'Exception' or 'ValueError' rather than bare 'except:'.",
                )
            )
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each operator in `a and b and c` adds a decision branch
        self.complexity += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        name = node.name
        if not _DUNDER_PATTERN.match(name) and not _SNAKE_CASE_PATTERN.match(name):
            self.findings.append(
                StaticFinding(
                    code="PY_NAMING_FUNCTION",
                    severity="INFO",
                    message=f"Function name '{name}' does not follow PEP 8 snake_case naming convention.",
                    line_number=node.lineno,
                    suggestion=f"Rename '{name}' to snake_case format.",
                )
            )
        # Check for empty body with only pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append(
                StaticFinding(
                    code="PY_EMPTY_FUNCTION",
                    severity="INFO",
                    message=f"Function '{name}' has an empty body containing only 'pass'.",
                    line_number=node.lineno,
                    suggestion="Implement function logic or raise NotImplementedError.",
                )
            )
        self._track_depth(node)
        self.generic_visit(node)
        self._untrack_depth()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        name = node.name
        if not _PASCAL_CASE_PATTERN.match(name):
            self.findings.append(
                StaticFinding(
                    code="PY_NAMING_CLASS",
                    severity="INFO",
                    message=f"Class name '{name}' does not follow PEP 8 PascalCase naming convention.",
                    line_number=node.lineno,
                    suggestion=f"Rename '{name}' to PascalCase format.",
                )
            )
        self._track_depth(node)
        self.generic_visit(node)
        self._untrack_depth()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                self.findings.append(
                    StaticFinding(
                        code="PY_WILDCARD_IMPORT",
                        severity="WARNING",
                        message=f"Wildcard import 'from {node.module or ''} import *' pollutes namespace.",
                        line_number=node.lineno,
                        suggestion="Explicitly import required functions or classes.",
                    )
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                # Avoid single-character ambiguous names (l, O, I)
                if name in ("l", "O", "I"):
                    self.findings.append(
                        StaticFinding(
                            code="PY_AMBIGUOUS_VARIABLE",
                            severity="INFO",
                            message=f"Ambiguous single-character variable name '{name}' (can be confused with 1 or 0).",
                            line_number=node.lineno,
                            suggestion="Choose a more descriptive variable identifier.",
                        )
                    )
        self.generic_visit(node)


def analyze_python_code(source_code: str) -> StaticAnalysisResult:
    """
    Performs safe static AST analysis on Python 3 source code.
    Returns metrics, complexity, and structured findings.
    """
    raw_lines = source_code.splitlines()
    loc = len([line for line in raw_lines if line.strip() and not line.strip().startswith("#")])

    try:
        tree = ast.parse(source_code)
    except SyntaxError as err:
        return StaticAnalysisResult(
            language="Python 3",
            lines_of_code=max(1, loc),
            cyclomatic_complexity=1,
            max_nesting_depth=0,
            maintainability_score=20.0,
            findings=[
                StaticFinding(
                    code="PY_SYNTAX_ERROR",
                    severity="ERROR",
                    message=f"Syntax Error: {err.msg}",
                    line_number=err.lineno,
                    suggestion="Fix Python syntax error before submission.",
                )
            ],
        )

    visitor = _PythonASTVisitor()
    visitor.visit(tree)

    # Complexity checks
    if visitor.complexity > 10:
        visitor.findings.append(
            StaticFinding(
                code="PY_HIGH_COMPLEXITY",
                severity="WARNING",
                message=f"High cyclomatic complexity ({visitor.complexity}). Code has many branching execution paths.",
                line_number=1,
                suggestion="Simplify conditional logic and break down complex algorithms into modular functions.",
            )
        )

    # Maintainability score calculation
    score = 100.0
    for finding in visitor.findings:
        if finding.severity == "ERROR":
            score -= 15.0
        elif finding.severity == "WARNING":
            score -= 5.0
        elif finding.severity == "INFO":
            score -= 2.0

    if visitor.complexity > 8:
        score -= min(25.0, (visitor.complexity - 8) * 2.0)
    if visitor.max_nesting_depth > 3:
        score -= min(20.0, (visitor.max_nesting_depth - 3) * 4.0)

    maintainability_score = round(max(0.0, min(100.0, score)), 1)

    return StaticAnalysisResult(
        language="Python 3",
        lines_of_code=max(1, loc),
        cyclomatic_complexity=visitor.complexity,
        max_nesting_depth=visitor.max_nesting_depth,
        maintainability_score=maintainability_score,
        findings=visitor.findings,
    )
