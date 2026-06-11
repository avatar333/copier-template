# OCP Deployment Manifests

## Goal

Add OpenShift manifests and Taskfile helpers so the `pe-forekat-admin` image can be deployed to a dedicated project with a predictable apply/delete flow.

## Current behavior

- The repository already builds a container image and runs the app with `gunicorn`.
- No OpenShift manifests exist under `contrib/deploy/ocp`.
- The README does not document an OpenShift deployment procedure.

## Desired behavior

- Provide manifests for:
  - project/namespace creation
  - ImageStream import from Nexus
  - Kubernetes `Deployment`
  - Service
  - Route
- Provide Taskfile tasks to apply and delete those manifests in order.
- Document the procedure in the README and note the `oc login` prerequisite.

## Implementation plan

1. Add manifests under `contrib/deploy/ocp`.
2. Add Taskfile tasks that call `oc apply` or `oc delete` against each manifest.
3. Update the README with a concise deployment section.
4. Verify the Taskfile syntax and review the final diff.

## Files likely to change

- `contrib/deploy/ocp/*`
- `Taskfile.yml`
- `README.md`

## Edge cases

- The app still needs runtime configuration from `config.yaml`; do not bake secrets into the image.
- The apply order should create the project first, then the ImageStream, import the external image, then apply the Deployment, Service, and Route.
- A Kubernetes `Deployment` does not behave exactly like `DeploymentConfig`; use the OpenShift image trigger annotation and ImageStream import task to keep the Deployment tied to the latest imported image.

## Verification plan

- Run `task --list` or equivalent Taskfile validation.
- Review the final diff before summarizing.

## Progress

- [x] Add planning note
- [x] Add manifests
- [x] Add Taskfile tasks
- [x] Update README
- [x] Verify Taskfile syntax and diff
