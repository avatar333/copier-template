# GitLab Image Build Gate

## Goal
- Prevent image build pipelines from running by default.
- Allow the build pipeline only when `BUILD_IMAGE=true` is explicitly supplied.
- Provide a Taskfile target that triggers the push with the required GitLab push option.

## Current Behavior
- `.gitlab-ci.yml` always defines the build job.
- There is no Taskfile in the repository.

## Desired Behavior
- Pipelines should only be created when `BUILD_IMAGE` is set to `true`.
- A `build-image` Taskfile task should push the current branch with `ci.variable="BUILD_IMAGE=true"`.

## Implementation Plan
1. Add a `workflow: rules` gate to `.gitlab-ci.yml`.
2. Keep the existing build job but make it depend on the workflow gate.
3. Add a root `Taskfile.yml` with a `build-image` task.
4. Verify the YAML remains minimal and readable.

## Files Likely To Change
- `.gitlab-ci.yml`
- `Taskfile.yml`

## Edge Cases
- Pipeline should remain disabled when `BUILD_IMAGE` is absent or false.
- The Taskfile should not alter any runtime build behavior beyond triggering the push option.

## Test / Verification Plan
- Inspect the final YAML manually.
- No runtime tests are needed for this CI config change.

## Progress Checklist
- [x] Inspect current CI config.
- [x] Add workflow gate.
- [x] Add Taskfile build task.
- [x] Review final diff.
