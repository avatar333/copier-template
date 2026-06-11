# Reference Dashboard UI Refresh

## Goal

Update the ForeKat Admin UI to visually match the `dashboard/` reference app and provided screenshot, without modifying anything under `dashboard/`.

## Current Behavior

- ForeKat uses a full-width top header and top navigation.
- Styling is dark blue with large rounded cards and pill buttons.
- The reference UI uses a fixed dark sidebar, compact top bar, muted panels, green primary actions, and dense admin dashboard cards.

## Desired Behavior

- ForeKat should use a sidebar application shell similar to the reference.
- Dashboard and common pages should keep existing functionality but use tighter panels, subdued borders, green primary actions, muted text, and icon-led navigation.
- The `dashboard/` project remains read-only reference material.

## Implementation Plan

1. Inspect reference templates/CSS and current ForeKat templates/CSS.
2. Update ForeKat `base.html` for sidebar/topbar layout and icon initialization.
3. Refresh shared CSS in `app/static/styles.css`.
4. Adjust dashboard markup for compact stat/action panels.
5. Run tests and inspect the final diff.

## Files Likely To Change

- `app/templates/base.html`
- `app/templates/dashboard.html`
- `app/static/styles.css`
- `tests/test_routes.py` if layout-sensitive assertions need adjustment

## Test/Verification Plan

- `.venv/bin/python -m pytest`

## Progress Checklist

- [x] Inspect reference and current UI files
- [x] Update ForeKat shell and styling
- [x] Update dashboard markup
- [x] Run tests
