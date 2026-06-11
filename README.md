# Copier Template Handoff

This directory is a self-contained snapshot of the current Flask + ForeKat project, packaged so you can copy it to a new location, initialize a fresh git repository there, and continue work with the same UI, layout, and operational decisions already captured.

## What This Template Is For

- Same dark blue operational dashboard look and feel
- Same sidebar/topbar structure and card layout
- Same loading page pattern with auto-submit flow
- Same documentation and runbook conventions
- Same OCP/container deployment shape

## How To Use It

1. Copy this directory to a new location.
2. Initialize a new git repository there.
3. Update the project name, hostnames, and environment-specific values.
4. Create or mount `config.yaml` for the new deployment.
5. Continue the next conversation from the notes in `CONTEXT.md`.

## Local Runbook

This snapshot keeps the same runbook as the source project:

```sh
bash scripts/bootstrap_venv.sh
source .venv/bin/activate
.venv/bin/flask --app run.py validate-config
.venv/bin/flask --app run.py db upgrade
.venv/bin/flask --app run.py run
```

## Design Notes

- The shared shell lives in `app/templates/base.html`.
- The visual system lives in `app/static/styles.css`.
- Loading behavior is driven by `app/templates/loading.html` and `app/static/js/loading_action.js`.
- The app is read-only toward Foreman/Katello.
- Assignment runs are synchronous and remain review-first.

## Important Operational Rules

- `config.yaml` is local runtime state and should not be committed.
- `db_details.txt` and `pat.txt` are bootstrap inputs only.
- The OCP image expects a mounted Secret named `pe-forekat-admin-config` in the source project version of this code.
- Gunicorn timeout and OpenShift route timeout were raised to support synchronous assignment generation.

## Where To Start

- Read `CONTEXT.md` for the conversation summary.
- Read `README.md` for the normal runbook and deployment notes.
- Start from `app/templates/base.html` and `app/static/styles.css` if you want the same UI feel in a new feature.
