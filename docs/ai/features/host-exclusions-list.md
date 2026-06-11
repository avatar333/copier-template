# Host Exclusions List

## Goal
- Add a persistent host exclusions list, expose it in the UI, and apply it before assignment generation.

## Current Behavior
- The dashboard has an Available Hosts card only.
- Assignment generation uses the selected Production or Non-Production pool without an exclusion layer.
- Excluded hosts are not persisted anywhere.

## Desired Behavior
- Dashboard copy should describe the Hosts Management area.
- A Host Exclusions List page should allow admin-managed storage of excluded FQDNs in MariaDB.
- Assignment generation should filter excluded hosts out of the selected pool before pet, special-group, prefix, and random assignment logic.

## Implementation Plan
1. Add a `HostExclusion` model and migration.
2. Add a DB-backed service helper to read and normalize exclusions.
3. Add the Host Exclusions List page and save flow.
4. Filter exclusions inside assignment persistence before the engine runs.
5. Add tests for dashboard wording, exclusions CRUD, and filtered assignment behavior.

## Files Likely To Change
- `app/models.py`
- `app/services/host_exclusions.py`
- `app/services/assignment_persistence.py`
- `app/services/host_inventory.py`
- `app/main.py`
- `app/templates/dashboard.html`
- `app/templates/host_exclusions.html`
- `app/templates/assignments.html`
- `migrations/versions/<new migration>.py`
- `tests/test_routes.py`
- `tests/test_assignment_persistence.py`
- `tests/test_assignment.py`

## Edge Cases
- Invalid FQDN-ish entries should fail without partial save.
- Empty exclusion submissions should clear the stored list.
- Excluded pets and special hosts should emit clear warnings.
- If all selected-pool hosts are excluded, the run should complete with zero assigned hosts and a clear warning.

## Test / Verification Plan
- Run focused route and persistence tests.
- Run the full pytest suite.
- Commands run:
  - `.venv/bin/python -m pytest tests/test_routes.py tests/test_assignment_persistence.py -q`
  - `.venv/bin/python -m pytest`

## Progress Checklist
- [x] Add model and migration.
- [x] Add exclusions service and page.
- [x] Filter exclusions in assignment generation.
- [x] Add tests.
- [x] Run `.venv/bin/python -m pytest`.
