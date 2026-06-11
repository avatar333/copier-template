# OCP Assignment Timeout

## Goal

Prevent assignment generation from being killed while ForeKat inventory requests are still running.

## Current behavior

- Assignment generation is synchronous.
- Gunicorn uses its default worker timeout unless configured otherwise.
- The OpenShift Route has no explicit timeout annotation.
- Long ForeKat `/hosts` pagination can exceed 30 seconds and produce worker timeouts or browser 504 responses.

## Desired behavior

- Gunicorn timeout is configurable and defaults high enough for assignment generation.
- The OpenShift Route timeout is long enough for the synchronous assignment request.
- README documents the timeout behavior.

## Implementation plan

1. Add `GUNICORN_TIMEOUT` to the container runtime command.
2. Set `GUNICORN_TIMEOUT` in the OCP Deployment.
3. Add the OpenShift Route timeout annotation.
4. Update README and verify manifests.

## Files likely to change

- `Containerfile`
- `contrib/deploy/ocp/20-deployment.yaml`
- `contrib/deploy/ocp/40-route.yaml`
- `README.md`

## Edge cases

- A long timeout keeps the synchronous flow working, but it does not turn assignment generation into background work.
- ForeKat request timeout still comes from `forekat.timeout_seconds` in `config.yaml`.

## Verification plan

- `task --list`
- `git diff --check`

## Progress

- [x] Add planning note
- [x] Update container timeout
- [x] Update OCP route/deployment
- [x] Update README
- [x] Run verification

## Verification

- `task --list` -> passed
- `git diff --check` -> passed
