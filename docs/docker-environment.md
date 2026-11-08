# Docker Local Infrastructure Guide

## 1. Overview & Architecture

The **Vedantu Online Coding Assessment Platform** uses Docker Compose to orchestrate local development infrastructure services. In Stage 2.4 and Stage 2.5, the platform establishes dedicated, isolated infrastructure services across decoupled networks:

### 1. Application Infrastructure (Stage 2.4)
- **PostgreSQL 16 (`postgres:16-alpine`)**: The primary ACID-compliant relational data store for the Vedantu application.
- **Redis 7 (`redis:7-alpine`)**: In-memory caching, session validation, and message queuing.
- Network: `vedantu-app-network` (Internal Docker bridge). Ports bound only to `127.0.0.1`.

### 2. Code Execution Infrastructure (Stage 2.5 - Judge0 CE v1.13.1)
- **Judge0 Server (`judge0/judge0:1.13.1`)**: REST API server running on Puma/Rails, serving submission requests and language introspection. Bound to `127.0.0.1:2358`.
- **Judge0 Worker (`judge0/judge0:1.13.1`)**: Execution worker running `./scripts/workers` with `COUNT=1`, bounded submission queue, and sandboxed Isolate execution.
- **Judge0 Dedicated PostgreSQL (`postgres:16-alpine`)**: Isolated relational store for Judge0 internal schema, migrations, and submission metadata. Zero sharing with application PostgreSQL.
- **Judge0 Dedicated Redis (`redis:7-alpine`)**: Isolated Resque job queue broker. Zero sharing with application Redis.

```text
Host (Developer Machine)
  |
  +-- 127.0.0.1:5432  --->  [ vedantu-postgres ]  <---+
  |                         (PostgreSQL 16 Alpine)    |
  |                         Volume: postgres_data      +--- [ vedantu-app-network ]
  |                                                    |    (Application Bridge Network)
  +-- 127.0.0.1:6379  --->  [ vedantu-redis ]     <---+
  |                         (Redis 7 Alpine + AOF)
  |                         Volume: redis_data
  |
  +-- 127.0.0.1:2358  --->  [ vedantu-judge0-server ] <--- [ vedantu-judge-network ]
                            (Judge0 CE v1.13.1 API)        (Published Host Port Bridge)
                                  |
                                  +--- [ vedantu-judge-internal-net ] (internal: true)
                                       |   (Zero Host Egress / Zero Cross-Network Route)
                                       +---> [ vedantu-judge0-workers ] (COUNT=1, Isolate sandbox)
                                       +---> [ vedantu-judge0-db ] (judge0_postgres_data)
                                       +---> [ vedantu-judge0-redis ] (judge0_redis_data)
```

> **Security & Network Isolation Guarantee**:
> In accordance with zero-trust architectural design, `vedantu-judge0-workers`, `vedantu-judge0-db`, and `vedantu-judge0-redis` reside exclusively on `vedantu-judge-internal-net` (`internal: true`).
> - The worker container has **no external network gateway** and **no default route to the host or internet**.
> - The worker container cannot route packets to `vedantu-app-network` (`172.18.0.0/16`), ensuring that untrusted user code executed in Judge0 can never access the application's PostgreSQL or Redis instances.
> - Isolate sandboxes run with network namespaces disabled (`--share-net=false`), allowing untrusted code access only to loopback `lo`.

---

## 2. Resource & Memory Limits

Under the ~3.5 GB WSL 2 / Docker Desktop memory budget, containers enforce strict memory limits:

| Service | Container Name | Image | Memory Limit | Typical Idle Usage |
|---|---|---|---|---|
| Application PostgreSQL | `vedantu-postgres` | `postgres:16-alpine` | `250M` | ~22 MiB |
| Application Redis | `vedantu-redis` | `redis:7-alpine` | `100M` | ~5 MiB |
| Judge0 DB | `vedantu-judge0-db` | `postgres:16-alpine` | `200M` | ~27 MiB |
| Judge0 Redis | `vedantu-judge0-redis` | `redis:7-alpine` | `100M` | ~5 MiB |
| Judge0 Server | `vedantu-judge0-server` | `judge0/judge0:1.13.1` | `450M` | ~96 MiB |
| Judge0 Workers | `vedantu-judge0-workers` | `judge0/judge0:1.13.1` | `700M` | ~195 MiB |
| **Total Allocation** | — | — | **~1.8 GB** | **~350 MiB** |

---

## 3. Configuration Files & Secrets

```text
VedantuCodingPlatform_New/
|-- docker/
|   |-- compose.yaml                  # Full Compose specification (App + Judge0 services)
|   `-- judge0.conf                   # Judge0 CE daemon configuration (COUNT=1, timeouts)
|-- scripts/
|   |-- validate_docker_env.py        # Python preflight validator (all 6 secrets checked)
|   `-- validate-docker-env.ps1       # Windows PowerShell preflight validator
|-- docs/
|   `-- docker-environment.md         # This runbook
|-- .env.example                      # Template tracking required variable names
`-- .env                              # Local developer secret values (git-ignored)
```

### Required `.env` Variables
```env
# Application Database & Cache (Stage 2.4)
POSTGRES_DB=vedantu_assessment_db
POSTGRES_USER=vedantu_admin
POSTGRES_PASSWORD=your_secure_dev_postgres_password
POSTGRES_PORT=5432

REDIS_PASSWORD=your_secure_dev_redis_password
REDIS_PORT=6379

# Judge0 Dedicated Database & Cache (Stage 2.5)
JUDGE0_DB_USER=judge0_admin
JUDGE0_DB_PASSWORD=your_secure_dev_judge0_db_password
JUDGE0_REDIS_PASSWORD=your_secure_dev_judge0_redis_password
JUDGE0_PORT=2358

# Judge0 Authentication & Security
JUDGE0_AUTHN_HEADER=X-Auth-Token
JUDGE0_AUTHN_TOKEN=your_secure_dev_judge0_token

# Internal FastAPI Development Secret
INTERNAL_DEV_SECRET=your_secure_dev_internal_secret
```

---

## 4. Preflight Password & Security Validation

Before starting or updating containers, run the preflight validation script:

```powershell
# Windows PowerShell Native Validator
powershell -ExecutionPolicy Bypass -File scripts/validate-docker-env.ps1

# Cross-Platform Python Validator
python scripts/validate_docker_env.py
```

The validation mechanism enforces:
1. All 6 secrets are defined, non-empty, and >= 16 characters in length.
2. Placeholder values (e.g. `replace_with_secure_dev_password`, `replace_with_secure_judge0_db_password`) are rejected.
3. No credentials or secrets are ever printed to logs or stdout.
4. Compose port bindings are validated within legal port ranges (1024-65535).

---

## 5. Docker Compose Operational Commands

All commands are executed from the project root (`E:\VedantuCodingPlatform_New`).

### 1. Validate Syntax & Compose Configuration
```powershell
docker compose -f docker/compose.yaml --env-file .env config
```

### 2. Start All Services
```powershell
docker compose -f docker/compose.yaml --env-file .env up -d
```

### 3. Check Running Service Health
```powershell
docker compose -f docker/compose.yaml --env-file .env ps
```

Expected output:
```text
NAME                     IMAGE                  COMMAND                  SERVICE          CREATED          STATUS                    PORTS
vedantu-judge0-db        postgres:16-alpine     "docker-entrypoint.s…"   judge0-db        X minutes ago    Up X minutes (healthy)    5432/tcp
vedantu-judge0-redis     redis:7-alpine         "docker-entrypoint.s…"   judge0-redis     X minutes ago    Up X minutes (healthy)    6379/tcp
vedantu-judge0-server    judge0/judge0:1.13.1   "/api/docker-entrypo…"   judge0-server    X minutes ago    Up X minutes              127.0.0.1:2358->2358/tcp
vedantu-judge0-workers   judge0/judge0:1.13.1   "/api/docker-entrypo…"   judge0-workers   X minutes ago    Up X minutes              2358/tcp
vedantu-postgres         postgres:16-alpine     "docker-entrypoint.s…"   postgres         X minutes ago    Up X minutes (healthy)    127.0.0.1:5432->5432/tcp
vedantu-redis            redis:7-alpine         "docker-entrypoint.s…"   redis            X minutes ago    Up X minutes (healthy)    127.0.0.1:6379->6379/tcp
```

### 4. Database Schema Migrations & Seeding (Stage 2.6)
Once `vedantu-postgres` is running healthy, apply the Alembic schema migrations and seed initial platform data:

```powershell
$env:PYTHONPATH="E:\VedantuCodingPlatform_New\backend"
.\backend\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
.\backend\.venv\Scripts\python.exe scripts/seed_database.py
```

### 5. Inspect Live Resource Consumption
```powershell
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

### 5. Review Service Logs
```powershell
# Follow Judge0 server logs
docker compose -f docker/compose.yaml --env-file .env logs -f judge0-server

# Follow Judge0 worker logs
docker compose -f docker/compose.yaml --env-file .env logs -f judge0-workers
```

### 6. Stop Services Safely
```powershell
docker compose -f docker/compose.yaml --env-file .env stop
```

---

## 6. Network Isolation & Security Verification

### Test 1: Worker Isolation from Application Database
Execute a network connectivity probe from `vedantu-judge0-workers` to `vedantu-postgres` (`172.18.0.2`):
```powershell
docker exec vedantu-judge0-workers python3 -c "
import socket
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('172.18.0.2', 5432))
    print('SECURITY VIOLATION: Connected to Application Database!')
except OSError:
    print('PASSED: Worker cannot reach application database (Network unreachable).')
"
```
*Expected: `PASSED: Worker cannot reach application database (Network unreachable).`*

### Test 2: Worker Isolation from the Internet
Verify that the worker cannot make outbound external connections:
```powershell
docker exec vedantu-judge0-workers python3 -c "
import socket
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('1.1.1.1', 53))
    print('SECURITY VIOLATION: Connected to Internet!')
except OSError:
    print('PASSED: Worker cannot reach external internet.')
"
```
*Expected: `PASSED: Worker cannot reach external internet.`*

### Test 3: Unauthenticated Access Rejection
Verify that Judge0 API rejects unauthenticated requests:
```powershell
curl.exe -i http://127.0.0.1:2358/system_info
```
*Expected: `HTTP/1.1 401 Unauthorized`*

### Test 4: Protected Internal Execution via FastAPI Backend
Execute a test submission through the FastAPI backend development endpoint:
```powershell
$secret = (Get-Content .env | Select-String "INTERNAL_DEV_SECRET=").Line.Split("=")[1].Trim()
$body = '{"source_code": "print(10 + 20)", "language": "python"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/internal/judge0/execute" `
    -Method Post `
    -Headers @{"X-Internal-Secret"=$secret; "Content-Type"="application/json"} `
    -Body $body
```
*Expected: `status: Accepted, status_id: 3, stdout: 30\n, is_passed: True`*

---

## 7. Troubleshooting & FAQ

| Issue | Root Cause | Resolution |
|---|---|---|
| `HTTP 401 Unauthorized` on Judge0 | `JUDGE0_AUTHN_TOKEN` mismatch or missing `X-Auth-Token` header. | Verify that `.env` defines `JUDGE0_AUTHN_HEADER=X-Auth-Token` and `JUDGE0_AUTHN_TOKEN`, and matches `judge0.conf`. |
| `HTTP 403 Forbidden` on `/api/v1/internal/judge0/execute` | Missing or invalid `X-Internal-Secret` header, or `INTERNAL_DEV_SECRET` is not set. | Pass header `-H "X-Internal-Secret: <token>"` matching `.env`. |
| `Failed to create control group /sys/fs/cgroup/memory` | Host runs pure cgroups v2 (WSL 2 / Docker Desktop). | Ensure submissions specify `enable_per_process_and_thread_time_limit: true` and `enable_per_process_and_thread_memory_limit: true`, which is automatically configured by `Judge0Service`. |
| `HTTP 429 Too Many Requests` on Internal Route | More than 3 concurrent requests attempted to execute simultaneously. | The built-in concurrency semaphore limits simultaneous executions to 3 in development mode. Wait for active jobs to finish. |
| `HTTP 413 Payload Too Large` | Submission payload exceeds 32 KB limit. | Reduce the size of `source_code` or `stdin` to stay within the 32 KB clamp. |
| `curl: (7) Failed to connect to 127.0.0.1:2358` | Docker network misconfiguration or `judge0-server` is not running. | Verify `docker compose -f docker/compose.yaml --env-file .env ps`. Ensure `judge0-server` is attached to `vedantu-judge-network` (bridge). |
