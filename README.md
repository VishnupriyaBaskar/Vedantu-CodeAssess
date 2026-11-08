# Vedantu Online Coding Assessment Platform

## 1. Project Overview
The **Vedantu Online Coding Assessment Platform** is an enterprise-grade, cloud-native assessment ecosystem designed to evaluate student programming skills through automated coding challenges, timed assessments, isolated sandboxed execution, and real-time performance analytics.

The platform provides:
- Automated, multi-language code compilation and sandboxed execution.
- Configurable assessment environments with server-authoritative countdown timers.
- Dual-layer evaluation combining deterministic automated test-case grading with advisory AI-driven qualitative code reviews.
- Configurable, privacy-compliant proctoring (webcam snapshots and browser focus tracking) with human-in-the-loop review.
- Multi-tier analytics delivering actionable learning-gap insights for students, instructors, and educational administrators.

---

## 2. Approved Technology Stack

The platform development stack is preserved strictly in accordance with approved Architecture Decision Records (ADR-01, ADR-02, ADR-03) and verified framework releases:

| Component | Technology | Defined Purpose |
|---|---|---|
| **Frontend Framework** | **Next.js 16 (App Router)** (Version: `16.4.5`) | Server-side rendered (SSR) & client-side web application interface. |
| **Frontend UI Library** | **React 19** (Version: `19.3.1`) | Modern component model with automatic memoization & concurrent features. |
| **Frontend Language** | **TypeScript 5** | Strict static typing and shared interfaces across the client application. |
| **Styling & Design** | **Tailwind CSS 3** (Version: `3.4.1`) | Responsive, accessible utility-first styling system. |
| **Backend Framework** | **FastAPI** | High-performance asynchronous REST & WebSocket API gateway. |
| **Backend Language** | **Python 3.11+** (Current: Python 3.11.9) | Core backend services, business logic, and asynchronous worker daemons. |
| **Primary Database** | **PostgreSQL 16** | ACID-compliant relational data store with JSONB support (`postgres:16-alpine`). |
| **Caching & Message Broker** | **Redis 7** | In-memory session validation, caching, and queuing (`redis:7-alpine`). |
| **Code Execution Sandbox** | **Judge0 Community Edition** | Self-hosted sandboxed code execution pinned to v1.13.1 on dedicated networks. |
| **Code Editor** | **Monaco Editor** | In-browser code editing with syntax highlighting, autocomplete, and language runtime switching (`@monaco-editor/react`). |
| **Code Evaluation** | **Deterministic Scoring + Static Analysis + AI Review** | Judge0 CE sandbox test-case grading combined with AST/lexical static analysis and provider-independent AI reviews. |
| **Container Orchestration** | **Kubernetes (AWS EKS)** | Production pod auto-scaling and container management (*planned for later phase*). |
| **Cloud Infrastructure** | **AWS** | Production cloud hosting (EKS, Aurora, ElastiCache, S3, KMS) (*planned for later phase*). |

---

## 3. Initial Student Programming Languages

In accordance with approved **ADR-01 (Proposal B)**:
- **Initial Supported Runtimes (Phase 1)**:
  - **Python 3**
  - **Java (OpenJDK 17/21)**
- **Extensible 4-Pillar Architecture**:
  The execution engine is metadata-driven and decoupled from core business logic. Future runtimes (including C++, JavaScript, C#, Go, and Rust) can be onboarded seamlessly via:
  1. *Pillar 1 (Runtime Availability)*: Verified compiler/interpreter installed in the sandbox.
  2. *Pillar 2 (Configuration & Metadata)*: Database entry in `programming_languages` with execution flags and resource multipliers.
  3. *Pillar 3 (Editor Support)*: Monaco Editor syntax worker and question boilerplate stubs.
  4. *Pillar 4 (Verification Suite)*: Automated CI test suite validating compilation, TLE, MLE, and security jailing.

In accordance with approved **ADR-02 (Option A)**:
- Instructors configure permitted programming languages per assessment:
  - `ALL_ACTIVE`: Any globally enabled language.
  - `SELECTED`: Explicit subset restricted by the instructor (e.g., "Java only" or "Python only").

---

## 4. Repository Structure & Directory Roles

```text
VedantuCodingPlatform_New/
|
|-- docs/             # Requirements documents, PRD, Architecture Decision Records (ADRs)
|-- frontend/         # Next.js 16+ TypeScript web application
|   |-- src/
|   |   |-- app/          # Next.js App Router (pages, layout, globals.css)
|   |   |-- components/   # Reusable UI & layout components (Navbar, Footer)
|   |   |-- config/       # Centralized application environment configuration
|   |   |-- lib/api/      # Reusable native fetch API client & endpoint helpers
|   |   |-- types/        # TypeScript interfaces & API response models
|   |   |-- hooks/        # Custom React hooks (Stage 5+)
|   |-- public/       # Static assets and icons
|   |-- package.json  # Frontend dependencies & npm scripts (Next.js 16, React 19)
|   |-- eslint.config.mjs # ESLint 9 flat configuration
|   |-- tsconfig.json # TypeScript compiler configuration
|   |-- tailwind.config.ts # Tailwind CSS theme configuration
|   `-- .env.example  # Frontend environment configuration template
|-- backend/          # FastAPI Python modular monolith application & worker daemons
|   |-- app/
|   |   |-- api/routes/   # API route modules (health check)
|   |   |-- core/         # Configuration & application settings (Pydantic Settings)
|   |   |-- models/       # Database models (Stage 3+)
|   |   |-- schemas/      # Pydantic request/response schemas (Stage 3+)
|   |   |-- services/     # Business logic layer (Stage 3+)
|   |   `-- utils/        # Shared helper functions
|   |-- tests/            # Pytest test suite (health check verification)
|   |-- requirements.txt  # Compatible backend dependency ranges
|   |-- requirements-lock.txt # Exact tested frozen package versions
|   `-- .env.example      # Backend environment configuration template
|-- docker/           # Local Docker Compose configurations (Postgres, Redis, Judge0)
|-- infrastructure/   # Cloud-native infrastructure-as-code (Helm charts, EKS manifests)
|-- scripts/          # Automation scripts, database seeds, and sandbox verification runners
|-- tests/            # Platform-wide test suites (integration and security tests)
|-- .gitignore        # Comprehensive source-control ignore patterns
`-- README.md         # Project documentation and architectural status
```

---

## 5. Backend Local Development Guide

### Prerequisites
- Python 3.11.9 (or 3.11+)
- Windows PowerShell

### 1. Activating the Virtual Environment
Navigate to the `backend` directory and activate the local virtual environment:

```powershell
cd E:\VedantuCodingPlatform_New\backend
.\.venv\Scripts\Activate.ps1
```

> *Tip: If script execution is restricted on Windows PowerShell, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` prior to activation.*

### 2. Installing Requirements
To install or synchronize minimal backend dependencies:

```powershell
pip install -r requirements.txt
```

### 3. Configuring Environment Variables
Copy the template `.env.example` to `.env`:

```powershell
cp .env.example .env
```

### 4. Starting the FastAPI Development Server
Launch the development server with live reload:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Health Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **Interactive Swagger API Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **ReDoc Documentation**: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)

### 5. Running Database Migrations & Seeding
Apply Alembic migrations to the application PostgreSQL database:

```powershell
$env:PYTHONPATH="E:\VedantuCodingPlatform_New\backend"
.\backend\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
```

Seed initial system roles (ADMIN, INSTRUCTOR, STUDENT) and supported languages (Python 3, Java):

```powershell
$env:PYTHONPATH="E:\VedantuCodingPlatform_New\backend"
.\backend\.venv\Scripts\python.exe scripts/seed_database.py
```

### 6. Running Backend Automated Tests
Execute the full pytest suite within the virtual environment:

```powershell
$env:PYTHONPATH="E:\VedantuCodingPlatform_New\backend"
pytest -v
```

---

## 6. Frontend Local Development Guide

### Prerequisites
- Node.js 24 (Verified with Node.js v24.14.0 LTS)
- npm v11+ (Verified with npm v11.9.0)

### 1. Installing Frontend Dependencies
Navigate to the `frontend` directory and install packages:

```powershell
cd E:\VedantuCodingPlatform_New\frontend
npm install
```

### 2. Configuring Environment Variables
Copy the template `.env.example` to `.env.local`:

```powershell
cp .env.example .env.local
```

Default configuration:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. Starting the Development Server
Launch the Next.js 16 Turbopack development server on port 3000:

```powershell
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to inspect the application landing page and real-time backend health connectivity diagnostics.

### 4. Code Quality & Type Checking
Run TypeScript type validation without emitting files:

```powershell
npx tsc --noEmit
```

Run ESLint 9 analysis using the ESLint CLI:

```powershell
npm run lint
```

### 5. Production Build & Start
Create an optimized production build using Next.js 16 (Turbopack):

```powershell
npm run build
```

Run the production server locally:

```powershell
npm run start
```

---

## 7. Local Docker Infrastructure Guide (Stage 2.4)

### Prerequisites
- Docker Desktop for Windows (WSL 2 backend) or Docker Engine v24+ on Linux
- Docker Compose v2 (`docker compose` CLI plugin)
- Available ports on `127.0.0.1`: `5432` (PostgreSQL) and `6379` (Redis)

### 1. Environment Setup
Create a root-level `.env` file from the provided template:

```powershell
cp .env.example .env
```

Configure strong development passwords (minimum 16 characters) in `.env` for `POSTGRES_PASSWORD` and `REDIS_PASSWORD`.

### 2. Preflight Password Security & Environment Validation
Before starting services, run the automated preflight validator. It verifies variable completeness, port sanity, and enforces minimum password length (>= 16 characters) while rejecting template placeholder values:

```powershell
# Windows PowerShell Native Validator
powershell -ExecutionPolicy Bypass -File scripts/validate-docker-env.ps1

# Cross-Platform Python Validator
python scripts/validate_docker_env.py
```

### 3. Validating Docker Compose Configuration
Verify Compose syntax, variable interpolation, port bindings, and network isolation:

```powershell
docker compose -f docker/compose.yaml --env-file .env config
```

### 4. Starting Infrastructure Services
Launch PostgreSQL 16 and Redis 7 in background detached mode:

```powershell
docker compose -f docker/compose.yaml --env-file .env up -d
```

### 5. Inspecting Containers & Health Status
Check container status and healthcheck telemetry:

```powershell
docker compose -f docker/compose.yaml --env-file .env ps
```

### 6. Viewing Service Logs
Inspect real-time logs from both infrastructure containers:

```powershell
docker compose -f docker/compose.yaml --env-file .env logs
```

### 7. Safe Container Shutdown
Stop containers safely without risking persistent data loss:

```powershell
docker compose -f docker/compose.yaml --env-file .env stop
```

> **Warning**: Never use `docker compose down -v` during standard development, as it destroys the persistent `vedantu_postgres_data` and `vedantu_redis_data` volumes. Detailed operations and troubleshooting are documented in [docs/docker-environment.md](docs/docker-environment.md).

---

## 8. Development Status & Roadmap

### Implemented Functionality (Completed)
- [x] **Stage 2.1**: Workspace initialized at `E:\VedantuCodingPlatform_New`, Git initialized on `main`, PRD preserved, `.gitignore` established.
- [x] **Stage 2.2 & 2.2.1**: FastAPI backend foundation established:
  - Python 3.11.9 virtual environment initialized in `backend/.venv/`.
  - Pydantic Settings configuration reading environment variables.
  - Operational `/api/v1/health` endpoint distinguishing application version (`1.0.0`) and API version (`v1`).
  - Pytest test suite with 4 passing tests.
  - Dependency reproducibility via `requirements-lock.txt`.
- [x] **Stage 2.3 & 2.3-Upgrade**: Next.js 16 frontend foundation established:
  - Upgraded to **Next.js 16.4.5**, **React 19.3.1**, and **React DOM 19.3.1** on Node.js 24.
  - ESLint 9 flat configuration (`eslint.config.mjs`) using direct ESLint CLI.
  - Centralized environment configuration in `src/config/`.
  - Reusable native fetch API client with timeout and structured error handling in `src/lib/api/`.
  - Responsive, accessible landing page displaying frontend status, live backend health diagnostics, and retry functionality.
  - Passing TypeScript type check (`npx tsc --noEmit`), zero ESLint errors (`npm run lint`), and successful production build (`npm run build`).
- [x] **Stage 2.4**: Local Docker environment foundation established & preflight hardened:
  - Canonical `docker/compose.yaml` specification for PostgreSQL 16 Alpine and Redis 7 Alpine with AOF persistence.
  - Hardened Redis healthcheck utilizing `REDISCLI_AUTH` environment variable (zero command-line password exposure).
  - Automated preflight validation mechanism (`scripts/validate-docker-env.ps1` & `scripts/validate_docker_env.py`) rejecting empty passwords, template placeholders, and passwords shorter than 16 characters with zero secret leaking.
  - Localhost-only port bindings (`127.0.0.1:5432`, `127.0.0.1:6379`) preventing external network exposure.
  - Isolated internal bridge network (`vedantu-app-network`) completely decoupled from future untrusted code execution.
  - Persistent named volumes (`vedantu_postgres_data`, `vedantu_redis_data`) surviving container lifecycles.
  - Root `.env.example` with strict parameter expansion validation (`${VAR:?error}`).
  - Comprehensive operational and troubleshooting runbook in `docs/docker-environment.md`.

- [x] **Stage 2.5**: Self-Hosted Judge0 Community Edition (v1.13.1) integration & code execution foundation:
  - Pinned official `judge0/judge0:1.13.1` Docker infrastructure with dedicated PostgreSQL 16 and Redis 7 instances.
  - Hardened `judge0.conf` with worker `COUNT=1`, bounded submission queue `MAX_QUEUE_SIZE=100`, and `ALLOW_ENABLE_NETWORK=false`.
  - Decoupled two-tier bridge network architecture (`vedantu-judge-internal-net` with `internal: true`) ensuring zero TCP connectivity between untrusted workers and application PostgreSQL / Redis.
  - Asynchronous FastAPI service client (`backend/app/services/judge0_service.py`) supporting Base64 transcoding, dynamic language discovery (`/languages`), polling with backoff, and robust error handling.
  - Protected development execution endpoint (`POST /api/v1/internal/judge0/execute`) gated by `settings.ENVIRONMENT == 'development'`, `X-Internal-Secret` verification, 32 KB body clamp, and 3-worker concurrency admission limiter.
  - Automated unit and integration test suite (`backend/tests/test_judge0_service.py`) covering clean execution, TLE, MLE, compilation error, runtime error, auth rejection, and size limits.
  - Full regression pass: 16/16 backend pytest passing, Next.js 16 frontend build and ESLint passing.

- [x] **Stage 2.6**: PostgreSQL 16 & SQLAlchemy 2.0 Database Foundation Implementation:
  - Configured asynchronous connection pooling (`async_engine`) and session factory (`async_sessionmaker`) using psycopg 3 driver (`postgresql+psycopg://`).
  - Implemented transactional FastAPI dependency `get_db` with automatic rollback/commit lifecycle and `WindowsSelectorEventLoopPolicy` on Windows.
  - Authored comprehensive domain models with UUID primary keys: `User`, `Role`, `UserRole`, `Assessment`, `Question`, `ProgrammingLanguage`, `TestCase`, `Submission`.
  - Configured Alembic migration environment (`backend/alembic.ini`, `backend/alembic/env.py`) with async engine integration and dynamic settings override.
  - Generated and applied initial migration revision (`3faee3e02f86_initial_database_schema.py`) to `vedantu-postgres` (`PostgreSQL 16.15`).
  - Verified safe migration downgrade mechanics in an isolated, disposable test schema (`scripts/verify_migration_downgrade.py`) leaving production public schema intact at `head`.
  - Implemented idempotent database seeding pipeline (`scripts/seed_database.py`) provisioning platform roles (`ADMIN`, `INSTRUCTOR`, `STUDENT`) and initial languages (Python 3: Judge0 ID 71, Java: Judge0 ID 62).
  - Authored automated database test suite (`backend/tests/test_database.py`), expanding backend regression coverage to 24 passing tests (100% pass rate).
  - Documented full database architecture and ER diagrams in `docs/database-architecture.md`.

- [x] **Stage 3**: Core Authentication, User Management & Role-Based Access Control (RBAC):
  - Implemented Argon2id password hashing and validation (`argon2-cffi`) adhering to OWASP security guidelines.
  - Engineered dual-token JWT authentication: short-lived 15-minute access tokens and 7-day refresh tokens signed via HMAC-SHA256 with issuer and audience verification.
  - Configured real-time session invalidation and token blacklisting using `vedantu-redis` (`revoked_token:{jti}` with TTL auto-cleanup).
  - Implemented secure refresh token rotation to prevent token replay attacks.
  - Authored reusable authorization dependencies (`get_current_user`, `require_admin`, `require_instructor`, `require_student`) enforcing least-privilege RBAC.
  - Enforced safe student self-registration policy preventing privilege escalation (extra role claims rejected with HTTP 422).
  - Implemented complete authentication API endpoints: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `/auth/admin/users`, `/auth/instructor/dashboard`, `/auth/student/profile`.
  - Built clean frontend authentication foundation in Next.js 16 (`types/auth.ts`, `lib/auth/tokenStorage.ts`, `lib/api/auth.ts`, `context/AuthContext.tsx`, and `AuthSection.tsx`).
  - Added 16 new automated tests in `backend/tests/test_auth.py`, expanding test suite to 40 passing tests (100% pass rate).
  - Documented full architecture in `docs/authentication-and-rbac.md`.

### Planned Functionality (Upcoming Stages)
- [x] **Stage 4**: Question Bank, Assessment Orchestration, Monaco Editor & Deterministic Code Evaluation Engine:
  - Authored domain models and applied Alembic migration `9e7e46f4e4b1`: `AssessmentCandidate`, `AssessmentAttempt`, `CodeDraft`, `SubmissionTestCaseResult`, with updated `Assessment`, `Question`, `TestCase`, and `Submission`.
  - Implemented Question Bank management with difficulty/topic filtering, sample vs hidden testcase creation, and soft-delete archiving.
  - Enforced zero-leakage test case confidentiality: public schemas completely exclude confidential hidden testcase inputs and expected outputs.
  - Implemented Assessment Orchestration with lifecycle states (`DRAFT` -> `PUBLISHED` -> `IN_PROGRESS` -> `COMPLETED` -> `ARCHIVED`), question curation, publishing preflight validations, candidate student enrollment, and cohort examination analytics.
  - Implemented Student Examination Workflow with server-authoritative countdown timers, 15-second network transit grace periods, intermediate draft autosaving (`code_drafts`), and one-attempt-per-student database constraints.
  - Implemented Judge0 code evaluation service supporting Python 3 and Java runtimes, compilation error short-circuiting, sandbox timeout/network error mapping (`INTERNAL_ERROR`), and partial question marks calculation.
  - Implemented Deterministic Scoring Engine with row-lock concurrency protection (`with_for_update()`), selecting best scores per question, calculating percentages, and determining pass/fail against `passing_marks`.
  - Implemented complete Next.js 16 + React 19 frontend workspace with Monaco Editor (`@monaco-editor/react`), language switching, autosave status, sample runner, submit evaluator, and final scorecard.
  - Added 10 new comprehensive automated tests in `backend/tests/test_stage4.py`, expanding regression suite to 50 passing tests (100% pass rate).
  - Documented complete architecture across `docs/question-bank.md`, `docs/assessment-management.md`, `docs/submission-and-evaluation.md`, and `docs/scoring-engine.md`.
- [x] **Stage 5**: AI-Powered Code Evaluation & Static Code Analysis (Completed)
  - Implemented lightweight static code analysis for Python 3 (built-in AST parser) and Java (lexical/structural regex parser) without executing untrusted code on the FastAPI server.
  - Calculated cyclomatic complexity, nesting depth, and maintainability index (0–100), detecting code smells (bare except, wildcard imports, empty catch blocks, redundant boolean comparisons, System.gc, and naming convention violations).
  - Architected provider-independent qualitative evaluation (`BaseAIProvider`, `AIEvaluationService`):
    - Zero-cost deterministic `MockAIProvider` generating structured algorithmic approach reviews, complexity estimates ($O(N)$, $O(N^2)$, etc.), and actionable tips.
    - Optional external `GeminiAIProvider` activated only when `GEMINI_API_KEY` is configured, with robust network timeout and error handling.
  - Enforced zero-leakage confidentiality: confidential hidden test-case inputs and outputs are strictly prohibited and never transmitted to AI providers.
  - Preserved grading integrity: deterministic Judge0 test-case scoring remains authoritative; qualitative AI review is advisory and stored in a separate `submission_evaluations` table (Alembic migration `a1b2c3d4e5f6`).
  - Added authenticated evaluation retrieval API (`GET /api/v1/student/submissions/{id}/evaluation`) enforcing strict submission ownership checks and RBAC.
  - Enhanced frontend workspace (`StudentAssessmentWorkspace.tsx`) with sub-tabs for Test Cases, Static Analysis metrics, and AI Qualitative Review.
  - Expanded backend test suite with 13 comprehensive tests in `backend/tests/test_stage5.py`, bringing total suite to 63 passing tests (100% pass rate).
  - Authored detailed architecture documentation in `docs/static-code-analysis.md` and `docs/ai-code-evaluation.md`.
- [ ] **Stage 6**: Student performance analytics, cohort mastery heatmaps, and instructor dashboards.
- [ ] **Stage 7**: Configurable webcam snapshot and browser focus proctoring telemetry with human-in-the-loop review.
- [ ] **Stage 8**: End-to-end security audits, load testing (2,000 concurrent test-takers), and AWS EKS cloud deployment.
