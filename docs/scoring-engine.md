# Deterministic Scoring Engine & Grading Architecture

**Project:** Vedantu Online Coding Assessment Platform  
**Workspace:** `E:\VedantuCodingPlatform_New`  
**Milestone:** Stage 4 — Question Bank, Assessment Orchestration & Code Evaluation

---

## 1. Mathematical Scoring Formula

The Vedantu Online Coding Assessment Platform employs a deterministic mathematical grading engine. Scoring is calculated at two hierarchical levels:
1. **Per-Question Scoring:** Computed dynamically based on the proportion of test case marks awarded.
2. **Per-Assessment Aggregate Scoring:** Computed by taking the best submission score per question across the candidate's session.

---

## 2. Question-Level Partial Scoring Formula

Each question in the Question Bank specifies:
- `question.marks` ($M_Q$): Total marks allocated to the problem (e.g. $20 \text{ pts}$).
- `test_cases`: Array of $N$ test cases, where each test case $i$ has an individual weight $w_i$.

Let the total configured test case marks be:

$$W_{\text{total}} = \sum_{i=1}^{N} w_i$$

If a test case passes (`status == "ACCEPTED"`), it awards $w_i$ marks. If it fails, times out, or errors, it awards $0$ marks:

$$w_{\text{awarded}, i} = \begin{cases} w_i & \text{if } \text{status}_i = \text{ACCEPTED} \\ 0 & \text{otherwise} \end{cases}$$

$$W_{\text{awarded}} = \sum_{i=1}^{N} w_{\text{awarded}, i}$$

The overall score awarded to the student's submission for question $Q$ is proportional to the question's total marks, rounded to two decimal places:

$$\text{Score}_Q = \text{round}\left(\frac{W_{\text{awarded}}}{W_{\text{total}}} \times M_Q, 2\right)$$

### Example Calculation
- Question Marks: $M_Q = 50 \text{ pts}$
- Test Case 1 (Sample): $w_1 = 10 \text{ pts}$ (PASSED $\rightarrow 10 \text{ awarded}$)
- Test Case 2 (Hidden): $w_2 = 10 \text{ pts}$ (FAILED $\rightarrow 0 \text{ awarded}$)
- $W_{\text{total}} = 20 \text{ pts}$, $W_{\text{awarded}} = 10 \text{ pts}$
- $$\text{Score}_Q = \text{round}\left(\frac{10}{20} \times 50, 2\right) = 25.0 \text{ pts}$$

---

## 3. Assessment-Level Aggregation & Pass/Fail Determination

When a student finishes an examination session (`POST /api/v1/student/assessments/{id}/finish`), the scoring engine calculates:

### 3.1 Best Submission Selection
Candidates are encouraged to refine and re-submit solutions during the examination. The platform selects the **maximum score achieved** for each question in the assessment:

$$\text{BestScore}(Q) = \max_{s \in \text{Submissions}(Q)} \text{Score}(s)$$

### 3.2 Total Assessment Score
The aggregate assessment score is the sum of best scores across all questions in the assessment:

$$\text{Total Score} = \sum_{Q \in \text{Assessment.Questions}} \text{BestScore}(Q)$$

### 3.3 Percentage
$$\text{Percentage} = \text{round}\left(\frac{\text{Total Score}}{\text{Assessment.TotalMarks}} \times 100.0, 2\right)$$

### 3.4 Pass/Fail Determination
The assessment defines a passing threshold `passing_marks` ($T_{\text{pass}}$):

$$\text{is\_passed} = \begin{cases} \text{True} & \text{if } \text{Total Score} \ge T_{\text{pass}} \\ \text{False} & \text{if } \text{Total Score} < T_{\text{pass}} \end{cases}$$

---

## 4. Concurrency Protection & Idempotency

### 4.1 Row-Level Locking (`with_for_update()`)
To prevent race conditions during rapid double-clicks or parallel browser requests when submitting an exam:
```python
att_stmt = (
    select(AssessmentAttempt)
    .where(
        AssessmentAttempt.assessment_id == assessment_id,
        AssessmentAttempt.user_id == user.id,
    )
    .with_for_update()
)
```
The attempt row is locked exclusively in PostgreSQL. If the attempt has already transitioned to `COMPLETED`, the scoring engine immediately returns the existing verified scorecard without recalculating or creating duplicate records.

---

## 5. Automated Verification & Testing

Validated in `backend/tests/test_stage4.py`:
- `test_deterministic_partial_marks_and_pass_fail_scoring`:
  - Enrolls student in an assessment with two 50-mark questions ($100 \text{ total marks}$, $50 \text{ passing marks}$).
  - Submits partial solution for Q1 ($25 \text{ pts}$) and complete solution for Q2 ($50 \text{ pts}$).
  - Verifies total score is exactly $75.0$, percentage is $75.0\%$, and `is_passed` is `True`.
  - Verifies duplicate submission is idempotent and maintains locked final score.
