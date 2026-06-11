# Assignment Source Dots

## Goal
- Replace textual assignment source labels in the Assigned Hosts box with colored dots plus accessible labels.

## Current Behavior
- Assigned host rows display source labels like `[random]`, `[prefix_sequence]`, and `[pet]`.
- Prefix sequence rows in the details table still render formatted source text for debugging.

## Desired Behavior
- The Assigned Hosts box should show colored dots for `random`, `prefix_sequence`, and `pet`.
- A compact key should explain the dots.
- Unknown or legacy source types should remain readable and safe.

## Implementation Plan
1. Add a small render-time source metadata helper in `app/main.py`.
2. Render assigned hosts as structured rows in the assignment template.
3. Add dot and key styles to the shared CSS.
4. Add route tests for the new markup and legacy source handling.

## Files Likely To Change
- `app/main.py`
- `app/templates/assignments.html`
- `app/static/styles.css`
- `tests/test_routes.py`

## Edge Cases
- Legacy or unknown `source_type` values must not break rendering.
- The visible key should remain compact and local to the Assigned Hosts box.

## Test / Verification Plan
- Run the assignment route tests.
- Run the full pytest suite.

## Progress Checklist
- [x] Inspect assignment rendering path and styles.
- [x] Patch source metadata helper and template.
- [x] Add CSS for dots and key.
- [x] Add regression tests.
- [x] Run tests.

## Commands Run
- `.venv/bin/python -m pytest tests/test_routes.py tests/test_assignment.py`
  - Result: `56 passed`
- `.venv/bin/python -m pytest`
  - Result: `129 passed`
