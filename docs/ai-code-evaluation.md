# AI-Powered Code Evaluation Architecture

## 1. Overview & Objective
Stage 5 introduces qualitative, educational AI code evaluation into the Vedantu Online Coding Assessment Platform. It reviews candidate source code for logical approach, readability, maintainability, algorithmic efficiency, and actionable optimization tips.

### Strict Core Principles
1. **Scoring Isolation:**
   - Automated Judge0 test-case evaluation remains the **authoritative basis** for grades and pass/fail decisions.
   - Qualitative AI feedback is purely advisory and **NEVER modifies** the numerical grade or test results.
2. **Confidentiality Invariant:**
   - **Confidential hidden test-case inputs or expected outputs are NEVER transmitted to AI providers.**
   - The evaluation request contains only:
     - Problem Title & Description
     - Constraints
     - Programming Language
     - Candidate Source Code
     - High-level execution summary (overall status, total passed/failed counts, score)
3. **Zero Mandatory Cost:**
   - The platform works out-of-the-box with a deterministic `MockAIProvider` requiring no API keys or internet connection.
   - External providers (e.g. Google Gemini) are optional and activated only when credentials are provided in `.env`.

---

## 2. Provider-Independent Architecture

```
                  ┌──────────────────────┐
                  │ AIEvaluationService  │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │   BaseAIProvider     │
                  └─────┬──────────┬─────┘
                        │          │
         ┌──────────────▼───┐  ┌───▼───────────────┐
         │  MockAIProvider  │  │ GeminiAIProvider   │
         │  (Deterministic, │  │ (Optional External │
         │   Zero-Cost)     │  │  API Integration)  │
         └──────────────────┘  └───────────────────┘
```

### Base Interface: `BaseAIProvider`
Located in `backend/app/services/ai_evaluation/base_provider.py`:
- `provider_name -> str`
- `async evaluate_code(request: AIEvaluationRequest) -> AIEvaluationResult`

### Mock AI Provider (`MockAIProvider`)
- Analyzes structural code properties (hash tables, nested loops, binary search, sorting, recursion).
- Provides deterministic, constructive feedback tailored to the pattern detected.
- Estimates asymptotic time complexity ($O(N)$, $O(N^2)$, $O(\log N)$, $O(N \log N)$) and space complexity ($O(1)$, $O(N)$).
- Status: always returns `COMPLETED`.

### Gemini AI Provider (`GeminiAIProvider`)
- Calls Google's Gemini models via official REST API (`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`).
- If `GEMINI_API_KEY` is not configured, returns status `UNAVAILABLE` without crashing.
- Implements strict timeout (15s) and catches network failures, returning status `FAILED`.
- Enforces strict JSON schema validation for responses.

---

## 3. Database Persistence (`submission_evaluations`)
Stored in dedicated table `submission_evaluations`:
- `id`: UUID (Primary Key)
- `submission_id`: UUID (Foreign Key `submissions.id`, CASCADE, Unique)
- `static_analysis`: JSON (AST metrics and structured findings)
- `ai_feedback`: JSON (Logical approach, complexity, readability, suggestions)
- `ai_provider`: String(50) (e.g. `mock`, `gemini-1.5-flash`)
- `ai_status`: String(50) (`COMPLETED`, `FAILED`, `UNAVAILABLE`, `SKIPPED`)
- `created_at`: DateTime(timezone=True)

---

## 4. API Endpoints

### 1. Submit Code for Full Evaluation
`POST /api/v1/student/assessments/{assessment_id}/submit-code`
- Executes code in Judge0 against all sample and hidden test cases.
- Computes deterministic score.
- Executes static analysis and qualitative AI review.
- Persists `Submission` and `SubmissionEvaluation`.
- Returns `SubmissionResponse` containing `test_case_results` and `evaluation`.

### 2. Retrieve Submission Evaluation
`GET /api/v1/student/submissions/{submission_id}/evaluation`
- **RBAC & Ownership Security:**
  - Candidate can only view evaluations of their own submissions (`403 Forbidden` if another student attempts access).
  - Instructors and Admins can view any candidate's evaluation.
- Returns `SubmissionEvaluationResponse`.
