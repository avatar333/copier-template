# ForeKat Flask Application

## Goal

Build a Flask web application that reads hosts from Foreman/Katello and assigns them as evenly as possible across local application users, persisting users, pets, and assignment runs in MariaDB.

## Current Behavior

The repository now has a working Flask scaffold, configuration loader, migration environment, local auth/user-management flow, a read-only ForeKat service layer for fetching hosts, and a UI for dashboard/hosts/pets/assignment runs. Assignment generation persists runs and exposes a per-run detail page with balance summaries and grouped output.

## Desired Behavior

- Flask application with login, CSRF protection, and hashed passwords
- MariaDB-backed persistence for local users, pets, and assignment history
- Config stored in `config.yaml`
- Foreman/Katello API integration using Basic auth with username + PAT
- UI for user management, host display, pets display, and assignment generation
- Deterministic business rules for pets, prefix/sequence groups, and random balancing

## Implementation Plan

1. Keep the dashboard and assignment-run views aligned with the stored assignment schema.
2. Keep the host and pet inventory views synchronized with the read-only ForeKat client.
3. Extend route and UI tests when new panels or redirects are added.
4. Re-run verification inside `.venv`.

## Files Likely To Change

- `.gitignore`
- `config.yaml`
- `requirements.txt`
- `README.md`
- `run.py`
- `scripts/bootstrap_venv.sh`
- `migrations/*`
- `app/*`
- `tests/*`

## Edge Cases

- Missing Foreman username or PAT in `config.yaml`
- No users or only one user during assignment
- Attempt to delete the last admin
- Attempt to demote the last admin
- Attempt to delete the currently logged-in admin when no other admin remains
- Pets that are not present in fetched host data
- Invalid or duplicate pet FQDN input
- Unsupported `per_page=all` behavior in Foreman/Katello pagination
- Large numeric page sizes timing out on the ForeKat API
- Collections that only expose host IDs instead of host objects
- Hosts or collections that return incomplete JSON payloads
- Existing users in a migrated database need unique generated login names
- Login names should be normalized and validated consistently across UI and CLI
- Non-matching hostnames that skip prefix/sequence grouping
- Prefix groups with single hosts that must fall through to random assignment
- Dashboard cards, hosts view, pets view, and assignment detail view all need to stay consistent with the latest route names

## Test/Verification Plan

- Import and syntax checks
- Unit tests for config validation and grouping logic
- Unit tests for assignment precedence and balancing
- Unit tests for admin-only user management rules and last-admin protections
- Unit tests for ForeKat pagination and normalization

## Progress Checklist

- [x] Review repository instructions and existing layout
- [x] Create scaffold and configuration files
- [x] Implement Flask app core and persistence
- [x] Implement Foreman/Katello integration
- [x] Implement assignment workflow and UI
- [x] Add tests
- [x] Run verification

## Decisions

- Target Python 3.14 because that is the interpreter currently available in the working environment.
- Use a standard Flask application factory layout with SQLAlchemy, Flask-Migrate, Flask-Login, and Flask-WTF.

## Known Limitations

- Live MariaDB and Foreman/Katello connectivity have not been verified in this run.

## Commands Run And Results

- `python3 --version` -> `Python 3.14.3`
- `rg --files` -> repository currently contains only guidance and bootstrap secret files
- `python3 -m venv .venv` -> created project virtual environment
- `python3 -m compileall app tests run.py` -> passed
- `.venv/bin/pip install -r requirements.txt` -> passed
- `.venv/bin/pip install pytest` -> passed
- `.venv/bin/pytest -q` -> `7 passed`
- `bash scripts/bootstrap_venv.sh` -> passed
- `.venv/bin/python -c "from app import create_app; ..."` -> import check passed
- `.venv/bin/flask --app run.py db init -d migrations` -> migration environment created
- `.venv/bin/pytest -q` -> `9 passed`
- model, auth, migration, and user CRUD alignment for `AppUser`/`PetHost`/`HostAssignment` implemented
- `python3 -m compileall app tests run.py` -> passed after auth/model updates
- `.venv/bin/pytest -q` -> `11 passed`
- service-package migration from `app/services.py` to `app/services/*` implemented
- `python3 -m compileall app tests run.py` -> passed after ForeKat service updates
- `.venv/bin/pytest -q` -> `17 passed`
- pure assignment engine and persistence wrapper implemented
- `python -m compileall app tests run.py migrations` -> passed
- `.venv/bin/pytest -q tests/test_assignment.py tests/test_assignment_persistence.py` -> `11 passed`
- `.venv/bin/pytest -q` -> `56 passed`
