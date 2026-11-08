# Vedantu Online Coding Assessment Platform
# Phase 7: Advanced Proctoring with Privacy Safeguards — Architecture & Specification

## 1. Executive Summary

Phase 7 implements **Advanced Proctoring with Privacy Safeguards** for the Vedantu Online Coding Assessment Platform. The proctoring system is designed around a fundamental ethical and legal principle: **Integrity monitoring should be transparent, respectful of candidate privacy, and strictly serve as advisory evidence for instructor audit—never as automated disqualification or punitive profiling.**

The system provides:
1. Candidate-side browser event tracking (tab switching, window focus/blur, fullscreen enforcement, page visibility, and navigation reloads).
2. Configurable local webcam presence indication with strict privacy boundaries (no facial recognition, no emotion inferencing, and no default video recording or storage).
3. A transparent rule-based suspicious activity detection engine that flags event frequency thresholds (with duplicate alert prevention).
4. Full candidate data isolation and instructor/admin cohort auditing workflows.

---

## 2. Privacy & Ethical Guardrails

The proctoring system enforces strict ethical and technical constraints:

1. **Explicit Notice & Consent:** Before monitoring begins, candidates are presented with a clear pre-exam integrity disclosure modal describing exactly what browser signals are monitored. Candidates must explicitly acknowledge and accept before entering the monitored examination.
2. **No Facial Recognition or Biometric Profiling:** The platform does not extract biometric templates, landmarks, or face IDs.
3. **No Emotion or Cognitive Inferencing:** The system strictly avoids pseudoscientific inferences of attention, honesty, or personality from facial expressions.
4. **No Continuous Footage Upload:** The candidate's video feed is rendered strictly locally (`<video autoPlay playsInline muted />`) for personal verification and presence. No video streams are transmitted to or stored on remote servers by default.
5. **Camera Technical Status Handling:** Camera permission denials or device disconnections are logged strictly as technical policy events (`CAMERA_PERMISSION_DENIED`, `CAMERA_UNAVAILABLE`), never as proof of cheating.
6. **No Automated Disqualification:** Alerts are classified as `LOW`, `MEDIUM`, or `HIGH` severity and serve exclusively as signals for instructor review. Only human instructors or administrators can review, escalate, or clear flags.
7. **Complete Stream Cleanup:** When an assessment is submitted or closed, all browser media stream tracks (`track.stop()`) are immediately terminated.

---

## 3. Proctoring Event Monitoring & Taxonomy

Every recorded event is assigned an immutable UTC timestamp, session link, candidate ID, and severity level:

| Event Type | Trigger | Severity | Metadata Captured |
|---|---|---|---|
| `TAB_SWITCH` | Candidate switches browser tab or minimizes window | `MEDIUM` | `{ trigger: "document_hidden" }` |
| `PAGE_HIDDEN` | Document visibility state changes to hidden | `LOW` / `MEDIUM` | `{ visibilityState: "hidden" }` |
| `PAGE_VISIBLE` | Candidate returns to assessment tab | `LOW` | `{ visibilityState: "visible" }` |
| `WINDOW_BLUR` | Assessment browser window loses focus | `LOW` | Timestamp |
| `WINDOW_FOCUS` | Assessment browser window regains focus | `LOW` | `{ blur_duration_seconds: number }` |
| `FULLSCREEN_EXIT` | Candidate exits required fullscreen mode | `MEDIUM` | None |
| `FULLSCREEN_ENTER` | Candidate enters fullscreen mode | `LOW` | None |
| `PAGE_RELOADED` | Candidate reloads page during active exam | `MEDIUM` | `{ trigger: "beforeunload" }` |
| `CAMERA_PERMISSION_DENIED` | Browser camera access prompt was denied | `LOW` | `{ error_name: "NotAllowedError" }` |
| `CAMERA_UNAVAILABLE` | No video input hardware found or device busy | `LOW` | `{ error_name: "NotFoundError" }` |
| `CAMERA_INTERRUPTED` | Video stream was interrupted or disconnected | `LOW` | Technical reason |

---

## 4. Rule-Based Suspicious Activity Detection Engine

The backend detection engine (`ProctoringService._evaluate_suspicious_activity`) processes ingested events against configurable thresholds and deduplicates alerts.

### 4.1 Rule Set & Thresholds

1. **Repeated Tab Switching (`REPEATED_TAB_SWITCHING`)**:
   - Condition: Candidate logs $\ge 2$ tab switches $\implies$ `MEDIUM` severity alert.
   - Condition: Candidate logs $\ge 4$ tab switches $\implies$ escalated to `HIGH` severity alert.
   - Explanation: *"Candidate switched browser tabs or minimized assessment window {count} times (Threshold: {threshold})."*

2. **Excessive Focus Loss (`EXCESSIVE_FOCUS_LOSS`)**:
   - Condition: Window blur count $\ge 3 \implies$ `MEDIUM` severity.
   - Condition: Cumulative blur duration $\ge 60$ seconds OR blur count $\ge 5 \implies$ `HIGH` severity.
   - Explanation: *"Candidate browser window lost focus {count} times totaling {seconds}s out of window focus."*

3. **Repeated Fullscreen Exits (`REPEATED_FULLSCREEN_EXIT`)**:
   - Condition: Fullscreen exits $\ge 2 \implies$ `MEDIUM` severity.
   - Condition: Fullscreen exits $\ge 3 \implies$ `HIGH` severity.
   - Explanation: *"Candidate exited required fullscreen examination mode {count} times."*

4. **Unexpected Navigation (`UNEXPECTED_NAVIGATION`)**:
   - Condition: Page reloads $\ge 2 \implies$ `MEDIUM` severity; $\ge 4 \implies$ `HIGH` severity.

5. **Multiple Suspicious Events Cluster (`MULTIPLE_SUSPICIOUS_EVENTS`)**:
   - Condition: Total non-camera suspicious events $\ge 8 \implies$ `HIGH` severity alert.

6. **Camera Policy Violation (`CAMERA_POLICY_VIOLATION`)**:
   - Condition: Webcam enabled on assessment, but candidate denied or disconnected camera $\implies$ `LOW` severity technical notice for instructor review.

---

## 5. Database Schema & Architecture

### 5.1 Tables

#### 1. `proctoring_sessions`
Tracks the 1-to-1 proctoring lifecycle for an assessment attempt:
```sql
CREATE TABLE proctoring_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_attempt_id UUID NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'INITIALIZED',
    consent_given BOOLEAN NOT NULL DEFAULT FALSE,
    consent_timestamp TIMESTAMPTZ,
    monitoring_config JSON,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    last_heartbeat_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_proctoring_sessions_attempt UNIQUE (assessment_attempt_id)
);
CREATE INDEX ix_proctoring_sessions_attempt_id ON proctoring_sessions(assessment_attempt_id);
CREATE INDEX ix_proctoring_sessions_assessment_id ON proctoring_sessions(assessment_id);
CREATE INDEX ix_proctoring_sessions_user_id ON proctoring_sessions(user_id);
CREATE INDEX ix_proctoring_sessions_status ON proctoring_sessions(status);
```

#### 2. `proctoring_events`
Stores immutable client-side audit logs:
```sql
CREATE TABLE proctoring_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proctoring_session_id UUID NOT NULL REFERENCES proctoring_sessions(id) ON DELETE CASCADE,
    assessment_attempt_id UUID NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'LOW',
    event_metadata JSON,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_proctoring_events_session_id ON proctoring_events(proctoring_session_id);
CREATE INDEX ix_proctoring_events_attempt_id ON proctoring_events(assessment_attempt_id);
CREATE INDEX ix_proctoring_events_event_type ON proctoring_events(event_type);
CREATE INDEX ix_proctoring_events_severity ON proctoring_events(severity);
CREATE INDEX ix_proctoring_events_recorded_at ON proctoring_events(recorded_at);
```

#### 3. `proctoring_alerts`
Stores instructor-facing suspicious activity alerts:
```sql
CREATE TABLE proctoring_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proctoring_session_id UUID NOT NULL REFERENCES proctoring_sessions(id) ON DELETE CASCADE,
    assessment_attempt_id UUID NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    explanation TEXT NOT NULL,
    related_event_ids JSON,
    review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    reviewed_by UUID REFERENCES users(id) ONDELETE SET NULL,
    review_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMPTZ
);
CREATE INDEX ix_proctoring_alerts_session_id ON proctoring_alerts(proctoring_session_id);
CREATE INDEX ix_proctoring_alerts_assessment_id ON proctoring_alerts(assessment_id);
CREATE INDEX ix_proctoring_alerts_review_status ON proctoring_alerts(review_status);
CREATE INDEX ix_proctoring_alerts_severity ON proctoring_alerts(severity);
```

#### 4. `assessments.proctoring_config`
Added nullable JSON column to table `assessments` to configure proctoring settings per examination.

---

## 6. API Specifications

Mounted under `/api/v1/proctoring`:

| Method | Endpoint | Authorization | Description |
|---|---|---|---|
| `POST` | `/api/v1/proctoring/sessions/start` | Candidate | Starts/resumes proctoring for active attempt; returns config & privacy terms. |
| `POST` | `/api/v1/proctoring/sessions/{id}/consent` | Candidate | Records explicit candidate consent (`consent: true`). |
| `POST` | `/api/v1/proctoring/sessions/{id}/events` | Candidate | Ingests batch of events and evaluates detection rules. |
| `POST` | `/api/v1/proctoring/sessions/{id}/heartbeat` | Candidate | Browser client keepalive ping every 20 seconds. |
| `POST` | `/api/v1/proctoring/sessions/{id}/end` | Candidate | Gracefully marks proctoring session as `ENDED`. |
| `GET` | `/api/v1/proctoring/sessions/{id}/status` | Candidate | Candidate-facing monitoring status and event counts. |
| `GET` | `/api/v1/proctoring/assessments/{id}/overview` | Instructor / Admin | Cohort proctoring KPIs, candidate summaries, and flagged list. |
| `GET` | `/api/v1/proctoring/assessments/{id}/events` | Instructor / Admin | Filterable raw proctoring event stream. |
| `GET` | `/api/v1/proctoring/assessments/{id}/alerts` | Instructor / Admin | Filterable suspicious activity alerts. |
| `GET` | `/api/v1/proctoring/attempts/{id}/report` | Instructor / Admin / Candidate | Detailed audit report for an attempt. |
| `PATCH` | `/api/v1/proctoring/alerts/{id}/review` | Instructor / Admin | Updates alert review status (`PENDING`, `REVIEWED`, `CLEARED`, `ESCALATED`) with notes. |

---

## 7. Candidate & Instructor User Journeys

### 7.1 Candidate Journey
1. **Assessment Entry:** Candidate clicks "Start Assessment" on an assigned test.
2. **Pre-Exam Consent Dialog:** Candidate is shown the integrity notice detailing fullscreen requirements, tab tracking, and webcam indicator (if configured). Candidate clicks "Accept Terms & Begin Examination".
3. **Workspace Monitoring:** Fullscreen mode is prompted. A compact "Integrity Active" badge glows green in the header. If webcam is enabled, a local self-preview PIP is shown in the bottom corner with a minimize toggle.
4. **Gentle Warning Notices:** If the candidate exits fullscreen or switches tabs, a soft amber toast notice appears: *"Integrity Notice: Please remain on your assessment window."*
5. **Exam Finalization:** When the candidate clicks "Finish Exam", proctoring media streams are terminated immediately (`track.stop()`) and the session is transitioned to `ENDED`.

### 7.2 Instructor Auditing Journey
1. **Overview Dashboard:** In Assessment Management, instructor clicks "Proctoring Audit" on any assessment card.
2. **Cohort Telemetry:** Displays total candidates, monitored sessions, flagged candidate count, total alerts, and high-severity flags.
3. **Candidate Summary Table:** Shows each student's attempt status, tab switches, fullscreen exits, window blurs, and review status.
4. **Detailed Audit Drawer:** Instructor clicks "View Audit" to inspect a student's full timeline, alerts, and explanations.
5. **Alert Review Workflow:** Instructor can mark alerts as `REVIEWED`, `CLEARED`, or `ESCALATED` and input official review notes.

---

## 8. Limitations & Best Practices

- **Browser-Side Event Boundaries:** Browser events can be affected by operating system notifications or accidental mouse movements. The platform intentionally avoids automatic penalties and requires human instructor judgment.
- **Hardware Diversity:** Candidates using virtual machines or systems without cameras are never blocked from completing coding assessments; permission denials are logged as technical notices.
