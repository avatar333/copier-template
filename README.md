# Copier UI Framework Starter

This directory is a self-contained UI framework snapshot. Copy it to a new location, initialize a new git repository there, and use it as the starting point for a new Flask UI with the same dark-blue look and feel.

## What This Starter Is For

- Shared dark-blue dashboard styling
- Sidebar, card, table, and loading-page layout
- Responsive page shell and reusable template structure
- Documentation page styling and content patterns
- Login-page presentation

## What This Starter Does Not Include

- ForeKat-specific backend services
- Database models or migrations
- Assignment generation logic
- Export logic
- OpenShift manifests or runtime bootstrap code

## How To Use It

1. Copy this directory to a new location.
2. Initialize a new git repository there.
3. Keep `app/templates/base.html` and `app/static/styles.css` as the visual source of truth.
4. Wire the templates into your own Flask app or equivalent backend.
5. Continue the next conversation from the notes in `CONTEXT.md`.

## Design Notes

- The shared shell lives in `app/templates/base.html`.
- The visual system lives in `app/static/styles.css`.
- Loading behavior is driven by `app/templates/loading.html` and `app/static/js/loading_action.js`.
- The documentation page is provided as an example of the same visual system applied to a content-heavy page.

## Where To Start

- Read `CONTEXT.md` for the conversation summary.
- Start from `app/templates/base.html` and `app/static/styles.css` if you want the same UI feel in a new feature.
- Use `app/templates/login.html`, `dashboard.html`, and `loading.html` as examples of the common page patterns.
