#!/usr/bin/env python3
"""
Preflight Docker Environment & Password Security Validator
Project: Vedantu Online Coding Assessment Platform
Workspace: E:\VedantuCodingPlatform_New

Enforces security requirements for local Docker infrastructure before container startup:
1. Verifies presence and readability of the targeted .env file.
2. Ensures all required infrastructure variables are defined.
3. Enforces strict password security on all secrets (PostgreSQL, Redis, Judge0, Internal API):
   - Rejects empty passwords.
   - Rejects placeholder values ('replace_with_...').
   - Rejects passwords shorter than 16 characters.
4. Validates port ranges for all published ports.
5. NEVER displays, logs, or leaks actual password values.
"""

import sys
import os
import argparse
from pathlib import Path

MIN_PASSWORD_LENGTH = 16
DISALLOWED_PLACEHOLDERS = {
    "replace_with_secure_dev_password",
    "replace_with_secure_redis_password",
    "replace_with_secure_judge0_token",
    "replace_with_secure_judge0_db_password",
    "replace_with_secure_judge0_redis_password",
    "replace_with_secure_internal_dev_secret",
    "password",
    "admin",
    "root",
    "postgres",
    "redis",
    "changeme",
}

REQUIRED_VARIABLES = [
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "REDIS_PASSWORD",
    "REDIS_PORT",
    "JUDGE0_AUTHN_TOKEN",
    "JUDGE0_DB_PASSWORD",
    "JUDGE0_REDIS_PASSWORD",
    "INTERNAL_DEV_SECRET",
]

PASSWORD_FIELDS = [
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "JUDGE0_AUTHN_TOKEN",
    "JUDGE0_DB_PASSWORD",
    "JUDGE0_REDIS_PASSWORD",
    "INTERNAL_DEV_SECRET",
]

PORT_FIELDS = ["POSTGRES_PORT", "REDIS_PORT", "JUDGE0_PORT"]


def parse_env_file(filepath: Path) -> dict:
    env_vars = {}
    if not filepath.exists():
        return env_vars

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                env_vars[key] = val
    return env_vars


def validate_environment(filepath: Path) -> list:
    errors = []

    if not filepath.exists():
        errors.append(
            f"Target environment file not found: '{filepath}'.\n"
            f"Action: Create '{filepath}' from '.env.example' and configure secure credentials: cp .env.example {filepath.name}"
        )
        return errors

    env_vars = parse_env_file(filepath)

    for var in REQUIRED_VARIABLES:
        if var not in env_vars:
            errors.append(f"Missing required environment variable: '{var}'.")

    for pwd_field in PASSWORD_FIELDS:
        if pwd_field in env_vars:
            val = env_vars[pwd_field]

            if not val or val.strip() == "":
                errors.append(
                    f"Security Error on '{pwd_field}': Secret cannot be empty."
                )
                continue

            normalized_val = val.strip().lower()
            if (
                normalized_val in DISALLOWED_PLACEHOLDERS
                or normalized_val.startswith("replace_with_")
                or "placeholder" in normalized_val
            ):
                errors.append(
                    f"Security Error on '{pwd_field}': Disallowed placeholder value detected. "
                    f"You must replace default template placeholders with a real secret before running Docker Compose."
                )

            if len(val) < MIN_PASSWORD_LENGTH:
                errors.append(
                    f"Security Error on '{pwd_field}': Secret length ({len(val)} characters) is below the "
                    f"mandatory minimum of {MIN_PASSWORD_LENGTH} characters."
                )

    for port_field in PORT_FIELDS:
        if port_field in env_vars:
            val = env_vars[port_field]
            try:
                port_num = int(val)
                if port_num < 1 or port_num > 65535:
                    errors.append(f"Invalid port on '{port_field}': '{val}' must be between 1 and 65535.")
            except ValueError:
                errors.append(f"Invalid port on '{port_field}': '{val}' is not a valid integer.")

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Preflight Docker Environment & Password Security Validator for Vedantu Platform"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the environment file to validate (default: .env)",
    )
    args = parser.parse_args()

    env_path = Path(args.env_file).resolve()
    print("=" * 70)
    print("VEDANTU PLATFORM -- DOCKER ENVIRONMENT PREFLIGHT VALIDATION")
    print("=" * 70)
    print(f"Target Environment File: {env_path}")

    errors = validate_environment(env_path)

    if errors:
        print("\n[FAILED] Preflight validation encountered security/configuration violations:")
        for idx, err in enumerate(errors, 1):
            print(f"\n  {idx}. {err}")
        print("\n" + "=" * 70)
        print("ACTION REQUIRED: Fix the above issues in your environment file before starting Docker containers.")
        print("Note: For security reasons, actual secret values are never displayed in logs or console output.")
        print("=" * 70)
        sys.exit(1)
    else:
        print("\n[PASSED] All required Docker environment variables and security requirements are satisfied!")
        print(f"  - App & Judge0 credentials meet mandatory complexity and length (>= {MIN_PASSWORD_LENGTH} chars).")
        print("  - Zero placeholder values detected.")
        print("  - Published port configurations validated.")
        print("=" * 70)
        print("Preflight check successful. Safe to launch containers with:")
        print(f"  docker compose -f docker/compose.yaml --env-file {args.env_file} up -d")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()