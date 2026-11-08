# Vedantu Online Coding Assessment Platform
# Phase 6: Adaptive Assessment Engine Architecture & Technical Specification

## 1. Executive Summary

Phase 6 implements the **Adaptive Assessment Engine** for the Vedantu Online Coding Assessment Platform. The engine transforms the platform from a static evaluation system into a personalized learning and diagnostic platform. It continuously tracks student performance across distinct programming topics, computes explainable Bayesian-smoothed topic mastery scores, dynamically suggests optimal problem difficulty, pinpoints conceptual strengths and weaknesses, generates tailored question recommendations with transparent pedagogical rationales, and supports self-paced interactive coding practice with full sandbox execution, automated testing, static analysis, and AI qualitative feedback.

---

## 2. Mathematical Mastery Model & Formulation

To avoid small-sample volatility (e.g., a student solving one trivial question achieving a false 100% mastery) and account for problem difficulty and retry penalties, topic mastery is calculated using a **Bayesian smoothed weighted model**:

### 2.1 Formula

$$\text{Mastery Score} = \frac{M_{\text{prior}} \times K + \sum_{i=1}^{N} \left( S_i \times W(D_i) \times \delta(A_i) \right)}{K + \sum_{i=1}^{N} W(D_i)}$$

Where:
- $M_{\text{prior}} = 30.0$: Prior mastery percentage (conservative baseline for new candidates).
- $K = 1.5$: Bayesian pseudo-observation weight regulating initial sensitivity.
- $N$: Total distinct questions attempted by the student in that topic.
- $S_i \in [0.0, 100.0]$: Maximum score percentage achieved on question $i$.
- $W(D_i)$: Difficulty weight for question $i$:
  - $\text{EASY} = 1.0$
  - $\text{MEDIUM} = 1.5$
  - $\text{HARD} = 2.0$
- $\delta(A_i)$: Attempt decay penalty factor based on attempts $A_i$ required to solve question $i$:
  $$\delta(A_i) = \max(0.70, 1.0 - (A_i - 1) \times 0.05)$$
  This rewards first-attempt accuracy while ensuring persistent students maintain at least 70% of credit.

### 2.2 Mastery Level Classifications

| Mastery Score Range | Classification | Description |
|---|---|---|
| $0.00 \le \text{Score} < 40.00$ | `BEGINNER` | Foundational syntax and basic logic still developing |
| $40.00 \le \text{Score} < 70.00$ | `DEVELOPING` | Working competency; occasional edge-case failures |
| $70.00 \le \text{Score} < 85.00$ | `PROFICIENT` | Consistent, reliable implementation and problem solving |
| $85.00 \le \text{Score} \le 100.00$ | `ADVANCED` | High-efficiency mastery across complex scenarios |

### 2.3 Confidence Metric

Confidence indicates how well-substantiated the mastery estimate is:
- **`LOW`**: Attempts $< 3$
- **`MEDIUM`**: $3 \le \text{Attempts} < 7$
- **`HIGH`**: Attempts $\ge 7$

---

## 3. Dynamic Difficulty Adjustment Engine

The platform adapts challenge difficulty per topic dynamically using hysteresis to prevent thrashing:

### 3.1 Transition Rules

1. **Escalation to Hard (`HARD`)**:
   - Condition: Mastery $\ge 75.0$, success rate on Medium questions $\ge 70\%$, and at least 2 Medium questions solved.
2. **Escalation to Medium (`MEDIUM`)**:
   - Condition: Mastery $\ge 50.0$ and success rate on Easy questions $\ge 60\%$.
3. **De-escalation to Medium (`MEDIUM`) from Hard**:
   - Condition: 3 consecutive failed/low-scoring attempts on Hard questions or Mastery falling below $60.0$.
4. **De-escalation to Easy (`EASY`) from Medium**:
   - Condition: Mastery falling below $35.0$ with at least 2 failed attempts.

---

## 4. Strengths & Weaknesses Identification

Topics with assessment or practice activity are partitioned into actionable diagnostic buckets:

- **Strong Topics (`strong_topics`)**: Mastery $\ge 70.0$ and confidence in (`MEDIUM`, `HIGH`).
- **Needs Improvement (`needs_improvement_topics`)**: Mastery $< 50.0$ with at least 1 attempted question.
- **Improving Topics (`improving_topics`)**: Upward longitudinal trajectory ($\Delta \text{score} \ge +5.0\%$ over the last 3 snapshots) or mastery between $50.0$ and $69.9$.
- **Unattempted Topics (`unattempted_topics`)**: System-curated topics with zero attempted submissions.

Every diagnostic categorization yields human-readable, actionable recommendations (e.g., *"Focus on algorithmic time complexity and corner-case validation in Dynamic Programming before retrying Hard problems"*).

---

## 5. Intelligent Question Recommendations

### 5.1 Candidate Selection & Filtering
Questions are chosen from the active question bank subject to strict business constraints:
1. `is_archived == False`.
2. Must belong to active assessment topics.
3. **Excluded**: Questions where the student has already achieved a passing score ($\ge 50\%$).

### 5.2 Scoring Heuristic & Ranking
Candidates are scored based on pedagogical relevance:
- **Topic Alignment Score**:
  - Questions in `needs_improvement_topics` receive $+40$ points.
  - Questions in `improving_topics` receive $+25$ points.
  - Questions in `unattempted_topics` receive $+20$ points (broadening curriculum exposure).
- **Difficulty Alignment Score**:
  - Matches candidate's recommended difficulty for that topic: $+30$ points.
  - Adjacent difficulty: $+10$ points.
- **Freshness**: Unattempted questions receive $+10$ points over previously failed ones.

---

## 6. Database Architecture & Schema

### 6.1 `student_topic_mastery`
Stores aggregate state per student and topic:
```sql
CREATE TABLE student_topic_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic VARCHAR(100) NOT NULL,
    mastery_score DOUBLE PRECISION NOT NULL DEFAULT 30.0,
    mastery_level VARCHAR(20) NOT NULL DEFAULT 'BEGINNER',
    confidence_level VARCHAR(20) NOT NULL DEFAULT 'LOW',
    recommended_difficulty VARCHAR(20) NOT NULL DEFAULT 'EASY',
    total_attempts INTEGER NOT NULL DEFAULT 0,
    solved_count INTEGER NOT NULL DEFAULT 0,
    last_score DOUBLE PRECISION,
    trend_direction VARCHAR(20) NOT NULL DEFAULT 'STABLE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_student_topic UNIQUE (user_id, topic)
);
CREATE INDEX ix_student_topic_mastery_user_id ON student_topic_mastery(user_id);
CREATE INDEX ix_student_topic_mastery_topic ON student_topic_mastery(topic);
```

### 6.2 `topic_mastery_history`
Maintains immutable longitudinal timeline snapshots:
```sql
CREATE TABLE topic_mastery_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic VARCHAR(100) NOT NULL,
    mastery_score DOUBLE PRECISION NOT NULL,
    mastery_level VARCHAR(20) NOT NULL,
    event_trigger VARCHAR(50) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_topic_mastery_history_user_topic ON topic_mastery_history(user_id, topic);
CREATE INDEX ix_topic_mastery_history_recorded_at ON topic_mastery_history(recorded_at);
```

---

## 7. Interactive Practice Workspace Workflow

1. **Discovery & Selection**: Student selects a recommended challenge or clicks a topic to practice.
2. **Confidentiality Enforcement**: Only sample test cases are returned to the client browser. Hidden test cases remain strictly in database storage.
3. **Execution Options**:
   - **Run Sample**: Executes code against visible sample test cases via Judge0 sandbox.
   - **Submit Solution**: Evaluates code against hidden test cases, runs Python AST/Java lexical static analysis, triggers AI qualitative code evaluation, updates `StudentTopicMastery` synchronously in the database, and records a `PRACTICE_SUBMISSION` snapshot into `TopicMasteryHistory`.

---

## 8. API Endpoint Specifications

All endpoints are mounted under `/api/v1/adaptive` and enforce JWT authentication:

| Endpoint | Method | Role | Description |
|---|---|---|---|
| `/api/v1/adaptive/mastery` | GET | `student`, `instructor`, `admin` | Fetches overall mastery summary and topic registry. |
| `/api/v1/adaptive/strengths-weaknesses` | GET | `student`, `instructor`, `admin` | Returns categorised strengths, weaknesses, and improvement advice. |
| `/api/v1/adaptive/performance` | GET | `student`, `instructor`, `admin` | Aggregates questions attempted/solved, accuracy, and difficulty breakdown. |
| `/api/v1/adaptive/recommendations` | GET | `student`, `instructor`, `admin` | Returns tailored question suggestions with explanations. |
| `/api/v1/adaptive/history` | GET | `student`, `instructor`, `admin` | Longitudinal historical snapshots for progress charting. |
| `/api/v1/adaptive/practice/{id}` | GET | `student`, `instructor`, `admin` | Sanitized practice problem definition (sample test cases only). |
| `/api/v1/adaptive/practice/{id}/run` | POST | `student`, `instructor`, `admin` | Fast sandbox run against sample test cases. |
| `/api/v1/adaptive/practice/{id}/submit` | POST | `student`, `instructor`, `admin` | Full evaluation, static analysis, AI evaluation, and mastery update. |

---

## 9. Security & Access Control

1. **Student Isolation**: Candidates can only access their own mastery records and history (`user_id = current_user.id`).
2. **Staff Access**: Instructors and administrators can view any candidate's analytics by passing `?student_id=<UUID>`.
3. **Sandbox Isolation**: Practice code execution routes directly through isolated Judge0 Docker sandboxes with strict CPU, memory, timeout, and network isolation.
4. **Zero Test Case Leakage**: Hidden test cases are never transmitted over public APIs.
