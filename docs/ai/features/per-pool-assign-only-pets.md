# Per-Pool Assign-Only Pets

## Goal
- Replace the single effective `Assign ONLY Pets` behavior with two independent per-pool settings:
  - `Assign ONLY Production Pets`
  - `Assign ONLY Non-Production Pets`

## Current Behavior
- Users already have separate `Production Pets` and `Non-Production Pets` lists.
- Assignment generation already filters pets by selected pool.
- The app still uses one legacy boolean field, `assign_only_pets`, to exclude a user from all non-pet assignments in every pool.

## Desired Behavior
- Production runs should only respect `assign_only_production_pets`.
- Non-Production runs should only respect `assign_only_non_production_pets`.
- The existing split-pets UI and behavior must remain intact.
- The legacy `assign_only_pets` field should remain safe and backward-compatible during the transition.

## Implementation Plan
1. Add two new boolean user fields and a migration that backfills them from the legacy field.
2. Update forms and user create/edit flows to save the new fields.
3. Add the new checkboxes inside the matching pet sections without changing the existing pet widgets.
4. Update assignment eligibility logic to use the selected pool’s assign-only field.
5. Update user list and assignment result display.
6. Add and update tests for both pools, both flags, and legacy-safe behavior.

## Files Likely To Change
- `app/models.py`
- `app/forms.py`
- `app/users.py`
- `app/main.py`
- `app/services/assignment_engine.py`
- `app/templates/user_form.html`
- `app/templates/users.html`
- `app/templates/assignments.html`
- `migrations/versions/*`
- `tests/test_assignment.py`
- `tests/test_routes.py`
- `tests/test_users.py`

## Edge Cases
- Existing users already using legacy `assign_only_pets` need a safe migration path.
- Production runs must ignore the Non-Production assign-only flag.
- Non-Production runs must ignore the Production assign-only flag.
- The special JBoss grouping must continue to honor pets first and selected-pool assign-only exclusions.

## Decisions
- Keep `assign_only_pets` in the schema for now as a legacy field.
- Backfill both new flags from `assign_only_pets` so existing behavior remains conservative after migration.

## Test / Verification Plan
- Run targeted assignment, route, and user tests.
- Run the full pytest suite.

## Progress Checklist
- [x] Inspect current split-pets and legacy assign-only implementation.
- [x] Patch model, migration, forms, routes, and templates.
- [x] Patch assignment logic for selected-pool flags.
- [x] Add and update tests.
- [x] Run `.venv/bin/python -m pytest`.

## Commands Run
- `.venv/bin/python -m pytest tests/test_assignment.py tests/test_users.py tests/test_routes.py tests/test_assignment_persistence.py`
  - Result: `87 passed`
- `.venv/bin/python -m pytest`
  - Result: `128 passed`
