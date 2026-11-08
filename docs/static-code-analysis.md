# Static Code Analysis Architecture

## 1. Overview & Objective
The Static Code Analysis engine evaluates submitted student solutions for structural quality, cyclomatic complexity, nesting depth, naming conventions, and common code smells in **Python 3** and **Java**.

### Strict Security Invariant
**Student source code is NEVER executed during static analysis.**
Analysis is conducted entirely through safe Abstract Syntax Tree (AST) parsing (Python) and lexical token parsing (Java) on the FastAPI server, preventing any possibility of malicious student code executing outside the dedicated Judge0 sandbox container.

---

## 2. Python 3 AST Analyzer

### Architecture
Located in `backend/app/services/static_analysis/python_analyzer.py`, the Python analyzer uses Python's standard `ast.parse` and custom `ast.NodeVisitor` subclass `_PythonASTVisitor`.

### Detected Rules & Code Smells
1. **Cyclomatic Complexity (`PY_HIGH_COMPLEXITY`):**
   - Base complexity = 1.
   - Decision points (`If`, `While`, `For`, `AsyncFor`, `ExceptHandler`, `BoolOp`, `Assert`) increment complexity.
   - Threshold > 10 triggers a warning to refactor code into modular functions.
2. **Deep Nesting (`PY_DEEP_NESTING`):**
   - Tracks block depth through compound statements.
   - Depth > 3 triggers a warning to decompose nested blocks into smaller helper functions.
3. **Bare Except (`PY_BARE_EXCEPT`):**
   - Catches `except:` without an exception type (which masks `SystemExit` and `KeyboardInterrupt`).
   - Advises catching specific exceptions like `Exception` or `ValueError`.
4. **Wildcard Imports (`PY_WILDCARD_IMPORT`):**
   - Flags `from module import *` for polluting the global namespace.
5. **Naming Conventions (`PY_NAMING_FUNCTION`, `PY_NAMING_CLASS`):**
   - Enforces PEP 8: `snake_case` for functions/methods (excluding dunders) and `PascalCase` for classes.
6. **Ambiguous Identifiers (`PY_AMBIGUOUS_VARIABLE`):**
   - Flags single-character ambiguous variable names (`l`, `O`, `I`).
7. **Syntax Errors (`PY_SYNTAX_ERROR`):**
   - Gracefully catches `SyntaxError` without crashing, returning an ERROR finding and low maintainability score (20/100).

---

## 3. Java Lexical and Structural Analyzer

### Architecture
Located in `backend/app/services/static_analysis/java_analyzer.py`, the Java analyzer performs regex-based lexical and structural analysis without needing JVM compilation.

### Detected Rules & Code Smells
1. **Branch Complexity (`JAVA_HIGH_COMPLEXITY`):**
   - Counts decision points (`if`, `else if`, `for`, `while`, `case`, `catch`, ternary `?`).
   - Complexity > 10 triggers a warning to decompose complex routines.
2. **Deep Block Nesting (`JAVA_DEEP_NESTING`):**
   - Tracks sanitized open/close brace nesting level.
   - Depth > 4 triggers a nesting warning.
3. **Empty Catch Blocks (`JAVA_EMPTY_CATCH`):**
   - Detects swallowed exceptions: `catch (...) { }`.
4. **Redundant Boolean Comparisons (`JAVA_REDUNDANT_BOOLEAN`):**
   - Detects `== true`, `== false`, `!= true`, `!= false`.
5. **Explicit Garbage Collection (`JAVA_SYSTEM_GC`):**
   - Detects `System.gc()`, advising candidates to let the JVM GC manage memory.
6. **Naming Conventions (`JAVA_NAMING_CLASS`, `JAVA_NAMING_METHOD`):**
   - Enforces `PascalCase` for classes/interfaces and `camelCase` for methods.

---

## 4. Maintainability Index Formula
Maintainability is scored from **0.0 to 100.0**:
$$\text{Score} = 100.0 - \sum \text{Penalties}$$

- **Error Finding:** -15.0 pts
- **Warning Finding:** -5.0 pts
- **Info Finding:** -2.0 pts
- **High Cyclomatic Complexity:** $-2.0 \times (\text{CC} - 8)$ (max penalty -25.0 pts)
- **Deep Nesting:** $-4.0 \times (\text{Depth} - \text{Threshold})$ (max penalty -20.0 pts)
- Clamped strictly to $[0.0, 100.0]$.

---

## 5. API Response Schema
```json
{
  "language": "Python 3",
  "lines_of_code": 14,
  "cyclomatic_complexity": 3,
  "max_nesting_depth": 2,
  "maintainability_score": 96.0,
  "findings": [
    {
      "code": "PY_NAMING_FUNCTION",
      "severity": "INFO",
      "message": "Function name 'MyFunc' does not follow PEP 8 snake_case naming convention.",
      "line_number": 4,
      "suggestion": "Rename 'MyFunc' to snake_case format."
    }
  ]
}
```
