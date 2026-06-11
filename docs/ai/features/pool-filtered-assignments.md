# Pool-Filtered Assignments

## Goal

Support generating assignments from the literal Katello Host Collection `Production` or `Non-Production` as a host pool filter, without using Host Collections as assignment groups.

## Current Behavior

- The assignment engine uses pets, prefix/sequence groups, and random remainder hosts.
- Host Collections are not part of the assignment grouping logic.
- Assignment runs store the selected host pool metadata.
- The dashboard has pool-specific assignment generation actions.

## Desired Behavior

- Two assignment actions:
  - generate from `Production`
  - generate from `Non-Production`
- The selected Host Collection only filters which hosts are eligible for a run.
- Pets are assigned first only if they are present in the selected pool.
- Prefix/sequence grouping only considers hosts in the selected pool.
- Assignment runs store the selected pool metadata.
- The assignment result page shows the selected pool.
- Prefix/sequence group assignment has a configurable randomness window to avoid overly consistent user selection while remaining balanced.

## Implementation Plan

1. Reintroduce host collection lookup in the ForeKat client for pool filtering only.
2. Extend inventory helpers to return a pool-filtered host snapshot and pool metadata.
3. Extend assignment run persistence and schema to store pool information.
4. Add pool-specific assignment routes and dashboard actions.
5. Update the assignment engine so prefix groups use a configurable randomness window.
6. Add tests for pool filtering, missing/empty pool handling, pool metadata persistence, and randomness behavior.
7. Harden Host Collection index pagination so a bad/empty `per_page=all` response falls back to numeric pagination.
8. Use a targeted pool lookup path: fetch the collection index, match the requested collection, then fetch only that collection's detail.

## Files Likely To Change

- `app/services/forekat_client.py`
- `app/services/host_inventory.py`
- `app/services/assignment_persistence.py`
- `app/services/assignment_engine.py`
- `app/models.py`
- `app/main.py`
- `app/templates/dashboard.html`
- `app/templates/assignments.html`
- `app/config.py`
- `app/static/styles.css`
- `tests/test_forekat_client.py`
- `tests/test_host_inventory.py`
- `tests/test_assignment.py`
- `tests/test_assignment_persistence.py`
- `tests/test_routes.py`
- `tests/test_validate_config_cli.py`
- `migrations/versions/*`

## Edge Cases

- Missing `Production` or `Non-Production` collection
- Empty target collection
- Some collection members cannot be mapped to FQDNs
- Pets present in Foreman but outside the selected pool
- Deterministic results when a random seed is configured

## Test/Verification Plan

- `python -m pytest`
- Focused tests for pool filtering and assignment randomness

## Progress Checklist

- [x] Inspect current inventory, assignment, and route code
- [x] Implement pool-filtered host inventory
- [x] Persist pool metadata on assignment runs
- [x] Add pool-specific routes and UI
- [x] Add/update tests
- [x] Run pytest
- [x] Add migration branch merge to keep Alembic head linear
- [x] Harden Katello collection index lookup
