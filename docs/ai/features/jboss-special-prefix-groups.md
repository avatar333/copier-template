# JBoss Special Prefix Groups

## Goal

Add an explicit assignment exception that keeps specific JBoss hosts together as unsplittable prefix sequence groups for Production and Non-Production assignment pools.

## Current Behavior

- Pets are assigned first.
- Remaining hosts are grouped by the general prefix/sequence parser.
- Host Collections filter the eligible host pool but are not assignment groups.
- JBoss hosts with alternating site tokens do not form one general prefix/sequence group because `bry` and `pkl` produce different group keys.

## Desired Behavior

- For the `production` pool, the requested six production JBoss hosts are treated as one special prefix sequence group.
- For the `non_production` pool, the requested six non-production JBoss hosts are treated as one special prefix sequence group.
- Pets still take priority and are not reassigned.
- Present non-pet members of the special list are assigned together before normal prefix grouping.
- Missing special hosts produce a warning only when at least one special host is present.

## Implementation Plan

1. Add a hardcoded special-group mapping in `AssignmentEngine`.
2. Thread `pool_name` from assignment persistence into the engine.
3. Assign special JBoss groups after pets and before normal prefix grouping.
4. Use source type `prefix_sequence` with explicit source names.
5. Add focused assignment and route tests.

## Files Likely To Change

- `app/services/assignment_engine.py`
- `app/services/assignment_persistence.py`
- `tests/test_assignment.py`
- `tests/test_routes.py`

## Edge Cases

- Some expected JBoss hosts are missing from the selected pool.
- No expected JBoss hosts are present.
- One or more expected JBoss hosts are pets.
- Wrong pool should not activate the other pool's special group.
- Special hosts must not be assigned twice.

## Test/Verification Plan

- `.venv/bin/python -m pytest tests/test_assignment.py tests/test_routes.py`
- `.venv/bin/python -m pytest`

## Progress Checklist

- [x] Inspect assignment engine, persistence, UI grouping, and tests
- [x] Implement special group mapping and assignment pass
- [x] Add tests
- [x] Run tests
