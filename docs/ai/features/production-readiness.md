# Production Readiness Pass

## Goal

Perform a final hardening pass for production-readiness: documentation, config validation, sanitized errors, and centralized admin checks.

## Current Behavior

The app already has the core Flask UI, auth, ForeKat integration, and assignment engine. The runbook and CLI validation command needed a final pass.

## Desired Behavior

- A clear README/runbook for first run and operations
- A `validate-config` CLI that validates local config and optional ForeKat status
- Sanitized UI errors and no secret logging
- Centralized admin-only checks

## Implementation Plan

1. Add the `validate-config` CLI command.
2. Centralize admin permission helpers.
3. Sanitize assignment-generation failure output.
4. Expand README with a runbook and redacted config example.
5. Run the validator and full pytest suite.

## Files Likely To Change

- `app/config.py`
- `app/factory.py`
- `app/main.py`
- `app/permissions.py`
- `app/users.py`
- `app/services/forekat_client.py`
- `README.md`
- `tests/test_validate_config_cli.py`
- `docs/ai/features/production-readiness.md`

## Edge Cases

- Missing `config.yaml`
- Placeholder ForeKat username
- Invalid database credentials
- Optional ForeKat `/status` validation
- UI error messages with sensitive details

## Test/Verification Plan

- `python -m pytest`
- `flask validate-config`

## Progress Checklist

- [x] Read repository guidance and inspect current files
- [x] Add validation helpers and CLI command
- [x] Centralize permission checks
- [x] Update README/runbook
- [x] Add explicit regression coverage for missing ForeKat username validation
- [x] Run validation and full test suite

## Verification

- `.venv/bin/python -m pytest` -> `56 passed`
- `.venv/bin/flask validate-config` -> `Configuration is valid.`
