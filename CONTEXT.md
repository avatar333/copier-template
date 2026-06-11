# Context Handoff

This file preserves the design and implementation context that began with the prompt:

> I really like the page layout and the CSS used. How would you supply a reusable framework and in what form, so that I can have a drop-in suite I can place in an empty project directory and develop a site with all this context available for the same look and feel?

## Conversation Timeline

1. Reusable framework option:
   - A copyable starter repository was recommended instead of a library.
   - `Copier` was chosen as the best long-lived template mechanism.
2. Handoff packaging:
   - You asked to put the starter in a subdirectory here so it could be copied to a new location, turned into a git repository, and continued in a new chat.
   - A self-contained snapshot was created under `copier-template/`.
3. Application context that should carry forward:
   - The dark-blue dashboard and sidebar layout
   - The assignment-generation loading page
   - The documentation page explaining assignment logic
   - Pool-based assignments using `Production` and `Non-Production`
   - Host exclusions filtering before assignment
   - Pets-first handling
   - Prefix-sequence grouping
   - Special JBoss groups
   - Export, OCP deployment, and runtime config conventions
4. Operational context:
   - The app remains read-only toward Foreman/Katello
   - Runtime config is still provided via `config.yaml`
   - The container and OCP deployment use longer timeouts for synchronous assignment generation

## Summary Of The Decisions

1. The reusable framework should be a copyable starter repository rather than a library.
2. `Copier` is the preferred template mechanism when the starter needs to be kept up to date over time.
3. The starter should include:
   - a shared `base.html`
   - the dark blue theme in `styles.css`
   - loading-page behavior
   - a dashboard shell
   - the docs/runbook structure
   - the OCP/container deployment files
4. A `CONTEXT.md` file should preserve the design and operational decisions from this conversation.
5. The starter should be easy to copy into a new directory, then initialized as a fresh git project.

## Key Follow-Up Decisions

- The `Documentation` page was added to the sidebar to explain the assignment logic in-app.
- The loading page was simplified to a centered spinner and auto-submit flow.
- The OpenShift deployment uses:
  - an `ImageStream`
  - a Kubernetes `Deployment`
  - a mounted Secret for `config.yaml`
  - longer Gunicorn and route timeouts for synchronous assignment generation
- The app remains read-only toward Foreman/Katello.
- Assignment rules are still:
  - pool selection
  - exclusions
  - pets first
  - prefix-sequence groups
  - special JBoss groups
  - random remainder

## Important Runtime Notes

- `config.yaml` must be present or mounted.
- The OCP version uses a Secret named `pe-forekat-admin-config`.
- Gunicorn timeout was increased to support long ForeKat inventory fetches.
- The OpenShift route timeout was also increased.

## What To Carry Into The New Repository

- The template README and runbook
- The layout and CSS in `app/templates/base.html` and `app/static/styles.css`
- The loading flow
- The documentation page
- The deployment and runtime notes

## Next Chat Seed

When continuing in a new chat, point Codex at the copied starter directory and say that this is the reusable Copier-style scaffold built from the ForeKat Admin UI and deployment conventions.
