# Test Hardening

## Goal

Expand pytest coverage for the assignment engine, ForeKat client, and route access control so core behavior is pinned down without requiring live network access.

## Current Behavior

The app already has working auth, user CRUD, read-only ForeKat access, and assignment generation. Coverage exists but misses several edge cases and failure paths.

## Desired Behavior

- Assignment engine rules are covered for zero-user, zero-host, pet, prefix-sequence, random, and deterministic cases
- ForeKat client error paths and membership extraction are covered with mocked HTTP responses
- Route access-control and assignment generation flows are covered without calling live external services
- CSRF behavior is verified explicitly in a dedicated test

## Implementation Plan

1. Add focused engine tests for the missing balancing and grouping scenarios.
2. Add client tests for pagination, HTTP errors, invalid JSON, and collection extraction variants.
3. Add route tests for access control and mocked assignment generation.
4. Run pytest and fix regressions.

## Files Likely To Change

- `tests/test_assignment.py`
- `tests/test_forekat_client.py`
- `tests/test_routes.py`
- `tests/test_users.py`
- `tests/test_auth.py`
- `tests/conftest.py`
- `docs/ai/bugs/test-hardening.md`

## Edge Cases

- Zero users
- Zero hosts
- Duplicate pet ownership
- Missing pet inventory
- Non-contiguous prefix groups
- CSRF-enabled POST requests

## Test/Verification Plan

- `python -m pytest tests/test_assignment.py tests/test_forekat_client.py tests/test_routes.py tests/test_users.py tests/test_auth.py`
- `python -m pytest`

## Progress Checklist

- [x] Reviewed repository guidance and current test coverage
- [x] Add missing engine tests
- [x] Add missing client tests
- [x] Add route and CSRF coverage
- [x] Run pytest and fix failures

## Verification

- `.venv/bin/pytest -q tests/test_assignment.py tests/test_forekat_client.py tests/test_routes.py tests/test_users.py tests/test_auth.py` -> `46 passed`
- `.venv/bin/python -m compileall app tests run.py migrations` -> passed
- `.venv/bin/pytest -q` -> `56 passed`
