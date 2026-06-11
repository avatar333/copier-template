# Containerfile

## Goal
- Add a container build recipe for the Flask app that is suitable for OCP/GitLab CI usage.
- Avoid copying local bootstrap secrets into the image.

## Current Behavior
- No `Containerfile` exists.
- The application expects runtime configuration from `config.yaml`.

## Desired Behavior
- Build a minimal Python image that installs dependencies and runs the Flask app with Gunicorn on a container port.
- Keep `config.yaml`, `db_details.txt`, and `pat.txt` out of the build context.
- Make the runtime working directory writable by OpenShift-style arbitrary UIDs so the app can create `config.yaml` at startup if needed.

## Implementation Plan
1. Add a `Containerfile`.
2. Add a `.dockerignore` to exclude local config/bootstrap files and other build noise.
3. Keep the runtime command simple and container-friendly.

## Files Likely To Change
- `Containerfile`
- `.dockerignore`

## Edge Cases
- If `config.yaml` is not mounted or present in the container, startup will still fail because the app requires valid runtime configuration.
- The image must not assume a fixed runtime UID; OpenShift may inject a random UID at run time.

## Test / Verification Plan
- Inspect the generated image build instructions manually.
- No runtime build was performed in this session.

## Progress Checklist
- [x] Add `Containerfile`.
- [x] Add `.dockerignore`.
- [x] Review final diff.
