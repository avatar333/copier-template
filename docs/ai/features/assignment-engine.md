# Assignment Engine

## Goal

Implement the host assignment algorithm as a pure service with a thin persistence wrapper that saves assignment runs and warnings to MariaDB.

## Current Behavior

The repo currently has a database-backed assignment flow coupled to the app route and a minimal pet / prefix-sequence / random handling path.

## Desired Behavior

- Pure assignment engine with deterministic, testable inputs and outputs
- Pet prioritization, prefix/sequence grouping, and random balancing
- Atomic persistence of assignment runs, host assignments, and warnings
- Minimal coupling between the algorithm and Flask/SQLAlchemy

## Implementation Plan

1. Create `app/services/assignment_engine.py` with DTOs and a pure balancing engine.
2. Create a persistence wrapper that loads inventory/users from the DB and commits atomically.
3. Update the app route to call the persistence wrapper.
4. Replace the old DB-heavy assignment tests with pure engine tests plus one persistence smoke test.
5. Run the focused assignment test suite.

## Files Likely To Change

- `app/main.py`
- `app/services/assignment_engine.py`
- `app/services/assignment_persistence.py`
- `tests/test_assignment.py`
- `tests/test_assignment_persistence.py`
- `docs/ai/features/assignment-engine.md`

## Edge Cases

- Zero users
- Zero hosts
- Duplicate pet ownership conflicts
- Unknown pets not present in inventory
- Missing or duplicate pet ownership
- Prefix sequence gaps and short runs

## Test/Verification Plan

- Unit tests for pet precedence and warnings
- Unit tests for prefix grouping and random balancing
- Persistence smoke test with mocked inventory

## Progress Checklist

- [x] Read repository guidance and inspect current assignment code
- [x] Implement pure engine DTOs and algorithm
- [x] Implement persistence wrapper
- [x] Update app route wiring
- [x] Add and run focused tests

## Verification

- `python -m compileall app tests run.py migrations` - passed
- `pytest -q tests/test_assignment.py tests/test_assignment_persistence.py` - passed, 11 tests
- `pytest -q` - passed, 56 tests
