# Vedantu Online Coding Assessment Platform
# Phase 8: Analytics & Instructor Question Management — Architecture & Specification

## 1. Executive Summary

Phase 8 introduces the **Analytics & Instructor Question Management Module** to the Vedantu Online Coding Assessment Platform. It delivers an enterprise-grade reporting engine and an enhanced question authoring workflow designed to give instructors and academic leads real-time, evidence-based visibility into student learning, cohort progression, assessment difficulty, and question bank quality.

The module provides:
1. **Live Operational Dashboard KPIs:** Aggregated platform health metrics including total registered candidates, active vs. published assessments, completed vs. in-progress attempts, cohort average scores, pass percentages, and exam completion rates.
2. **Deep Assessment Performance Analytics:** Granular score distributions partitioned across standard percentiles, pass/fail ratios, topic proficiencies, difficulty distributions, individual candidate ranking tables, and integrated Phase 7 proctoring telemetry.
3. **Cohort-Level Progression & Gap Identification:** Systemic topic mastery profiles, difficulty distributions, identification of top performers, at-risk candidate detection (average score < 40%), and actionable warnings for frequently failed topics.
4. **Individual Candidate Audit Reports:** 360-degree performance views combining longitudinal topic mastery progression (reusing Phase 6 `StudentTopicMastery` models to prevent score divergence), strengths/weaknesses categorization, difficulty proficiencies, and submission histories with static analysis cyclomatic complexity and AI code quality summaries—while maintaining zero leakage of hidden evaluation test cases.
5. **Question Bank Quality & Categorization:** Enhanced question repository displaying attempt volumes, solved counts, and success rates. Test cases are strictly partitioned into three semantic tiers: `SAMPLE` (public), `FUNCTIONAL` (private validation), and `EDGE_CASE` (boundary conditions).
6. **Pre-Flight Publishing Validation:** Pre-publication diagnostic engine that verifies test case coverage, enforces mark alignment between test cases and questions, and flags empty input/output definitions.
7. **RFC 4180 Compliant CSV Exports:** One-click streaming exports for assessment results, candidate audit trails, and question bank quality metrics.
8. **Strict RBAC & Candidate Isolation:** All analytics and question management routes require authenticated `INSTRUCTOR` or `ADMIN` roles; candidates are strictly forbidden from viewing cohort data, fellow candidates' reports, or hidden test cases.

---

## 2. Database Schema Extensions

To support test case semantic tiering and question bank curation, the database schema was extended via Alembic migration `d4e5f6a7b8c9`:

```
               +-------------------------------------------+
               |                 questions                 |
               +-------------------------------------------+
               | id: UUID (PK)                             |
               | title: VARCHAR(255)                       |
               | problem_description: TEXT                 |
               | difficulty: VARCHAR(50)                   |
               | topic: VARCHAR(100)                       |
               | marks: INTEGER                            |
               | tags: VARCHAR(255) [Phase 8]              |
               | starter_code: TEXT [Phase 8]              |
               | is_archived: BOOLEAN                      |
               +-------------------------------------------+
                                     | 1
                                     |
                                     | *
               +-------------------------------------------+
               |                test_cases                 |
               +-------------------------------------------+
               | id: UUID (PK)                             |
               | question_id: UUID (FK -> questions.id)    |
               | input_data: TEXT                          |
               | expected_output: TEXT                     |
               | explanation: TEXT                         |
               | is_hidden: BOOLEAN                        |
               | category: VARCHAR(50) [Phase 8]           |
               |   ('SAMPLE', 'FUNCTIONAL', 'EDGE_CASE')   |
               | marks: INTEGER                            |
               | display_order: INTEGER                    |
               +-------------------------------------------+
```

### Database Migration Details
- **Migration Script:** `backend/alembic/versions/2026_11_08_1600-d4e5f6a7b8c9_phase8_analytics_and_question_mgmt.py`
- **Revision ID:** `d4e5f6a7b8c9`
- **Parent Revision:** `c3d4e5f6a7b8` (Phase 7 Proctoring)
- **Bidirectional Symmetry:** Tested and verified through `upgrade head`, `downgrade -1`, and `upgrade head` execution.

---

## 3. Test Case Taxonomy & Pre-Flight Validation

Test cases are categorized into three distinct functional tiers:

| Tier | Visibility | Intended Purpose | Example |
|---|---|---|---|
| `SAMPLE` | Public (`is_hidden: false`) | Publicly provided to candidates in the coding workspace to demonstrate input/output formats and verify basic understanding. | Input: `"5\n1 2 3 4 5"`, Output: `"15"` |
| `FUNCTIONAL` | Private (`is_hidden: true`) | Core correctness test cases used by Judge0 to verify functional implementation across typical operational inputs. | Input: `"3\n10 20 30"`, Output: `"60"` |
| `EDGE_CASE` | Private (`is_hidden: true`) | Stress-testing corner cases: negative numbers, empty arrays, max constraints, and single-element inputs. | Input: `"1\n-5"`, Output: `"-5"` |

### Pre-Flight Validation Engine (`POST /questions/{question_id}/validate`)
Before publishing an assessment or assigning questions, the validation engine checks:
1. **Sample Coverage:** Question must contain at least 1 public `SAMPLE` test case.
2. **Hidden Evaluation Coverage:** Question must contain at least 1 private `FUNCTIONAL` or `EDGE_CASE` test case.
3. **Mark Alignment:** Total marks allocated across test cases ($\sum \text{marks}_{\text{tc}}$) must match question `marks`. Discrepancies generate advisory warnings.
4. **Data Integrity:** Rejects empty or whitespace-only expected output strings.

---

## 4. Analytics Aggregation Architecture

The `AnalyticsService` (`backend/app/services/analytics_service.py`) executes high-efficiency, non-blocking asynchronous queries using SQLAlchemy 2.0 and `AsyncSession`. Full table loads are strictly avoided in favor of indexed group-bys and server-side aggregation.

### 4.1 Instructor Overview KPIs (`GET /analytics/instructor/overview`)
- **Total Candidates:** Distinct count of users possessing the `STUDENT` role.
- **Assessment Counts:** Total created vs. `status == "PUBLISHED"`.
- **Attempt Velocity:** `status == "COMPLETED"` vs. `status == "IN_PROGRESS"`.
- **Mean Score:** Server-side average of `AssessmentAttempt.percentage` across completed attempts.
- **Pass Rate:** $\frac{\text{Completed Attempts with is\_passed = true}}{\text{Total Completed Attempts}} \times 100\%$.
- **Completion Rate:** $\frac{\text{Completed Attempts}}{\text{Completed Attempts} + \text{Active Attempts}} \times 100\%$.

### 4.2 Assessment Performance (`GET /analytics/instructor/assessments/{assessment_id}`)
- **Score Distribution:** Five standard histogram buckets: $0\text{–}20\%$, $21\text{–}40\%$, $41\text{–}60\%$, $61\text{–}80\%$, $81\text{–}100\%$.
- **Topic & Difficulty Breakdown:** Average score achieved by candidates on submissions corresponding to questions in the assessment.
- **Candidate Rankings:** Tabular ranking sorted by score percentage, indicating completion status, score, max marks, outcome, and proctoring alert counts.
- **Phase 7 Proctoring Telemetry:** Monitored session count, total event volume, total alerts, pending reviews, and high-severity flags.

### 4.3 Cohort Performance (`GET /analytics/instructor/cohort`)
- **Mastery Proficiencies:** Reuses Phase 6 `StudentTopicMastery` records grouped by topic to calculate cross-student mean mastery.
- **Frequently Failed Topics:** Identifies topics with mean mastery $< 50\%$, rendering an actionable warning alert for instructors.
- **Top Performers & At-Risk Candidates:** Segregates students with mean completed exam score $\ge 70\%$ (top performers) and students with score $< 40\%$ (at-risk).

### 4.4 Candidate Performance Audit (`GET /analytics/instructor/candidates/{candidate_id}`)
- **Mastery Consistency:** Directly reads `StudentTopicMastery` and `TopicMasteryHistory` from Phase 6, ensuring absolute consistency between student self-views and instructor audit reports.
- **Strengths & Weaknesses:** Categorizes topics into Strengths ($\ge 70\%$) and Areas for Growth ($< 50\%$).
- **Confidential Submission History:** Returns code submission records with status, score, passed test case counts, AST cyclomatic complexity, and AI code quality scores without revealing hidden test case contents.

---

## 5. Security & Candidate Confidentiality Architecture

The platform enforces strict confidentiality and data isolation:

1. **Role-Based Access Control (RBAC):**
   - Endpoints under `/api/v1/analytics/*` and `/api/v1/questions/{id}/validate` enforce `require_instructor` (`INSTRUCTOR` or `ADMIN` roles).
   - Candidate tokens receive immediate `HTTP 403 Forbidden` responses.
2. **Hidden Test Case Confidentiality:**
   - Candidate endpoints (`/questions/{id}`) invoke `_to_public_response`, which filters `test_cases` strictly to `not tc.is_hidden`.
   - Candidate submission audit views expose test case pass/fail counts (`3/5 passed`), but never expose the internal input strings or expected outputs of private tests.
3. **Cross-Candidate Isolation:**
   - Candidates cannot query another candidate's performance reports or assessment attempts.

---

## 6. RFC 4180 CSV Export Specifications

All CSV downloads stream RFC 4180 compliant formatted data using Python's standard `csv.writer` with `io.StringIO`:

### 6.1 Assessment Results CSV (`/analytics/instructor/assessments/{id}/export`)
Headers:
```csv
Candidate ID,Full Name,Email,Status,Total Score,Max Marks,Percentage,Passed,Started At,Completed At,Proctoring Alerts
```

### 6.2 Candidate Performance Report CSV (`/analytics/instructor/candidates/{id}/export`)
Structured into four distinct sections:
1. `=== CANDIDATE OVERVIEW ===` (Candidate ID, Full Name, Email, Joined At, Attempted, Completed, Avg Score, Best Score, Strengths, Weaknesses)
2. `=== TOPIC MASTERY ===` (Topic, Mastery Score, Level, Confidence, Attempted, Solved, Success Rate, Trend)
3. `=== CODE SUBMISSION HISTORY ===` (Submission ID, Question Title, Topic, Difficulty, Language, Status, Score, Max Score, Tests Passed, Total Tests, Static Warnings, AI Quality Score, Submitted At)

### 6.3 Question Bank Performance CSV (`/analytics/instructor/questions/export`)
Headers:
```csv
Question ID,Title,Topic,Difficulty,Marks,Tags,Archived,Total Attempts,Solved Count,Success Rate (%),Average Score,Sample Tests,Functional Tests,Edge Cases,Total Test Marks,Created At
```

---

## 7. Frontend User Experience & UI Design System

The frontend is implemented with Next.js 16 (Turbopack), React 19, and Tailwind CSS. It follows a zero-external-dependency charting philosophy using responsive SVGs and Tailwind layout primitives:

1. **`InstructorAnalyticsDashboard.tsx`:** Primary view with 6 KPI summary cards, assessment selection dropdown, interactive score distribution histogram, topic mastery progress gauges, frequently failed topic warning banners, and student leaderboards.
2. **`AssessmentAnalyticsModal.tsx`:** Assessment deep dive modal featuring score extremes, pass/fail donuts, score distribution bars, proctoring telemetry banner, candidate submissions table, and direct CSV download.
3. **`CandidatePerformanceModal.tsx`:** 360-degree student audit drawer featuring topic mastery progression cards, strengths/weaknesses tags, difficulty level breakdown, and code submission history with static/AI evaluation summaries.
4. **Enhanced `QuestionBankSection.tsx`:** Integrated search filter by title, topic, or tags, quality indicator badges (solved count, success rate), test case suite manager for `SAMPLE`, `FUNCTIONAL`, and `EDGE_CASE` tiers, and interactive pre-flight publishing validation.
5. **Dashboard Navigation in `page.tsx`:** Added high-visibility "Analytics & Insights" tab alongside "Assessment Management", "Question Bank", and "Adaptive Learning".

---

## 8. Automated Verification Suite

The backend automated test suite (`backend/tests/test_analytics.py`) verifies all 7 critical architectural contracts:

1. `test_instructor_overview_and_rbac`: Verifies live KPI aggregation and student RBAC denial (403).
2. `test_assessment_analytics_and_distribution`: Verifies score distribution buckets (5 buckets), pass/fail counts, and 404 handling.
3. `test_cohort_analytics`: Verifies cross-student topic proficiencies and score distributions.
4. `test_candidate_report_and_isolation`: Verifies candidate audit trail and strict non-leakage of private test cases.
5. `test_question_test_case_management_and_validation`: Verifies question creation with tags/starter code, test case category updating via PUT, and pre-flight validation warnings.
6. `test_csv_exports`: Verifies RFC 4180 CSV generation and MIME types for assessments, candidates, and questions.

### Full Test Suite Results
- **Backend Tests:** 90 of 90 passed (`100%`) in `35.54s`.
- **TypeScript:** `npx tsc --noEmit --incremental false` passed with `0` errors.
- **Frontend Linter:** `eslint .` passed with `0` warnings and `0` errors.
- **Production Build:** `next build` (Next.js 16.4.5 Turbopack) completed successfully in `1.7s`.
