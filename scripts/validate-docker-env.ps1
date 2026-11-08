<#
.SYNOPSIS
    Preflight Docker Environment & Password Security Validator for Windows PowerShell.
.DESCRIPTION
    Validates the .env file before starting Docker Compose services:
    - Rejects empty passwords and secrets.
    - Rejects template placeholders ('replace_with_...').
    - Rejects secrets shorter than 16 characters.
    - Never displays actual secrets.
.PARAMETER EnvFile
    Path to the environment file (default: .env).
#>
[CmdletBinding()]
param(
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

$MinLength = 16
$DisallowedPlaceholders = @(
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
    "changeme"
)

$RequiredVars = @(
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "REDIS_PASSWORD",
    "REDIS_PORT",
    "JUDGE0_AUTHN_TOKEN",
    "JUDGE0_DB_PASSWORD",
    "JUDGE0_REDIS_PASSWORD",
    "INTERNAL_DEV_SECRET"
)

$PasswordFields = @(
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "JUDGE0_AUTHN_TOKEN",
    "JUDGE0_DB_PASSWORD",
    "JUDGE0_REDIS_PASSWORD",
    "INTERNAL_DEV_SECRET"
)

$PortFields = @("POSTGRES_PORT", "REDIS_PORT", "JUDGE0_PORT")

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "VEDANTU PLATFORM -- DOCKER ENVIRONMENT PREFLIGHT VALIDATION (POWERSHELL)" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Target Environment File: $EnvFile"

if (-not (Test-Path $EnvFile)) {
    Write-Host "`n[FAILED] Preflight validation encountered configuration violations:" -ForegroundColor Red
    Write-Host "`n  1. Target environment file not found: '$EnvFile'." -ForegroundColor Red
    Write-Host "     Action: Copy '.env.example' to '$EnvFile' and configure secure credentials: cp .env.example $EnvFile" -ForegroundColor Yellow
    Write-Host ("=" * 70) -ForegroundColor Cyan
    exit 1
}

$envMap = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $eqIndex = $line.IndexOf("=")
        if ($eqIndex -gt 0) {
            $key = $line.Substring(0, $eqIndex).Trim()
            $val = $line.Substring($eqIndex + 1).Trim()
            if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
                $val = $val.Substring(1, $val.Length - 2)
            }
            $envMap[$key] = $val
        }
    }
}

$errors = [System.Collections.Generic.List[string]]::new()

foreach ($var in $RequiredVars) {
    if (-not $envMap.ContainsKey($var)) {
        $errors.Add("Missing required environment variable: '$var'.")
    }
}

foreach ($pwdField in $PasswordFields) {
    if ($envMap.ContainsKey($pwdField)) {
        $val = $envMap[$pwdField]
        if ([string]::IsNullOrWhiteSpace($val)) {
            $errors.Add("Security Error on '$pwdField': Secret cannot be empty.")
            continue
        }

        $lowerVal = $val.Trim().ToLower()
        if ($DisallowedPlaceholders -contains $lowerVal -or $lowerVal.StartsWith("replace_with_") -or $lowerVal.Contains("placeholder")) {
            $errors.Add("Security Error on '$pwdField': Disallowed placeholder value detected. You must replace default template placeholders with a real secret.")
        }

        if ($val.Length -lt $MinLength) {
            $lenMsg = "Security Error on '" + $pwdField + "': Secret length (" + $val.Length + " characters) is below mandatory minimum of " + $MinLength + " characters."
            $errors.Add($lenMsg)
        }
    }
}

foreach ($portField in $PortFields) {
    if ($envMap.ContainsKey($portField)) {
        $val = $envMap[$portField]
        $portNum = 0
        if ([int]::TryParse($val, [ref]$portNum)) {
            if ($portNum -lt 1 -or $portNum -gt 65535) {
                $errors.Add("Invalid port on '$portField': '$val' must be between 1 and 65535.")
            }
        } else {
            $errors.Add("Invalid port on '$portField': '$val' is not a valid integer.")
        }
    }
}

if ($errors.Count -gt 0) {
    Write-Host "`n[FAILED] Preflight validation encountered security/configuration violations:" -ForegroundColor Red
    $idx = 1
    foreach ($err in $errors) {
        Write-Host "`n  $idx. $err" -ForegroundColor Red
        $idx++
    }
    Write-Host "`n"
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "ACTION REQUIRED: Fix the above issues in '$EnvFile' before starting Docker containers." -ForegroundColor Yellow
    Write-Host "Note: For security reasons, actual secret values are never displayed in logs or console output." -ForegroundColor DarkGray
    Write-Host ("=" * 70) -ForegroundColor Cyan
    exit 1
} else {
    Write-Host "`n[PASSED] All required Docker environment variables and security requirements are satisfied!" -ForegroundColor Green
    Write-Host "  - App & Judge0 credentials meet mandatory complexity and length (>= $MinLength chars)." -ForegroundColor Green
    Write-Host "  - Zero placeholder values detected." -ForegroundColor Green
    Write-Host "  - Published port configurations validated." -ForegroundColor Green
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "Preflight check successful. Safe to launch containers with:" -ForegroundColor White
    Write-Host "  docker compose -f docker/compose.yaml --env-file $EnvFile up -d" -ForegroundColor White
    Write-Host ("=" * 70) -ForegroundColor Cyan
    exit 0
}