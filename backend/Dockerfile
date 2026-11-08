# ==============================================================================
# Vedantu Online Coding Assessment Platform - Backend Dockerfile
# Production-ready, hardened, multi-stage container build for FastAPI
# Base image: python:3.11-slim
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create isolated Python virtual environment for application dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy pinned dependency lockfile
COPY requirements-lock.txt ./

# Install dependencies deterministically from lockfile
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-lock.txt

# ------------------------------------------------------------------------------
# Stage 2: Production Runtime Runner
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

WORKDIR /app

# Configure production environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    HOST=0.0.0.0 \
    PORT=8000

# Install curl for container health monitoring and cleanup package lists
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy pre-built virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create dedicated non-root application system user and group (UID/GID 1001)
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup --no-create-home appuser

# Copy application code, database migrations, and configuration with correct ownership
COPY --chown=appuser:appgroup alembic.ini ./
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup entrypoint.sh ./entrypoint.sh

# Ensure entrypoint script is executable
RUN chmod +x ./entrypoint.sh

# Switch to dedicated non-root user
USER appuser

# Expose FastAPI application port
EXPOSE 8000

# Container health check querying the native FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/api/v1/health || exit 1

# Configure entrypoint and default production command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
