# OCP Runtime Config Secret

## Goal

Make OpenShift runtime configuration explicit so pods do not bootstrap placeholder `config.yaml` values and then fail during startup validation.

## Current behavior

- The image can write `config.yaml` in `/opt/pe-forekat-admin`.
- If no valid `config.yaml`, `db_details.txt`, or `pat.txt` is mounted, the app generates placeholder config.
- Placeholder database values can surface as a dialect validation error instead of a clear placeholder error.

## Desired behavior

- The OCP Deployment mounts `config.yaml` from a Secret.
- The Taskfile creates or updates that Secret from a local, verified `config.yaml`.
- The README documents the Taskfile-based Secret flow.
- Validation reports TODO placeholders before dialect-specific checks.

## Implementation plan

1. Reorder validation checks so missing and placeholder values are reported before dialect validation.
2. Add a Secret volume mount for `config.yaml` in the Deployment manifest.
3. Add a Taskfile helper for creating or updating the config Secret.
4. Add a test for placeholder validation precedence.
5. Run targeted config tests and a diff check.

## Files likely to change

- `app/config.py`
- `contrib/deploy/ocp/20-deployment.yaml`
- `Taskfile.yml`
- `README.md`
- `tests/test_config.py`

## Edge cases

- Do not commit actual config or secrets.
- If the Secret is missing, the pod should fail at mount time instead of generating invalid placeholder config.

## Verification plan

- `.venv/bin/python -m pytest tests/test_config.py tests/test_config_parsing.py -q`
- `git diff --check`

## Progress

- [x] Add planning note
- [x] Update validation ordering
- [x] Mount config secret
- [x] Update README
- [x] Run verification

## Verification

- `.venv/bin/python -m pytest tests/test_config.py tests/test_config_parsing.py -q` -> `6 passed`
- `.venv/bin/python -m pytest` -> `159 passed`
