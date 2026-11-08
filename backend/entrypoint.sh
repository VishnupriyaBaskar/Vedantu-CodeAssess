#!/bin/sh
set -e

# ==============================================================================
# Vedantu Online Coding Assessment Platform - Backend Entrypoint
# ==============================================================================

# Run database migrations only if explicitly requested
# Default is disabled to prevent migration races in scaled deployments
if [ "${RUN_MIGRATIONS}" = "true" ] || [ "${RUN_MIGRATIONS}" = "1" ]; then
    echo "Applying database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "Database migrations applied successfully."
fi

# Execute the primary container command
exec "$@"
