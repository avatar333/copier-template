# Pet Widget Hidden Field Duplication

## Goal
- Restore saving add/remove changes from the Production Pets and Non-Production Pets widgets.

## Current Behavior
- The form renders `production_pet_blob` and `non_production_pet_blob` twice:
  - once through `form.hidden_tag()`
  - once inside each pet widget
- JavaScript updates the widget-local hidden input, but Flask reads the first submitted field value.

## Desired Behavior
- Each pet blob field should be submitted once, from the matching pet widget.
- CSRF protection should remain intact.

## Implementation Plan
1. Replace `form.hidden_tag()` with the CSRF token only.
2. Keep the widget-local hidden inputs as the authoritative submitted pet blobs.
3. Add a route/template regression test that each pet blob input is rendered once.

## Files Likely To Change
- `app/templates/user_form.html`
- `tests/test_routes.py`

## Test / Verification Plan
- Run the user form route test.
- Run the relevant user tests.

## Progress Checklist
- [x] Identify duplicate hidden field root cause.
- [x] Patch template.
- [x] Add regression test.
- [x] Run tests.

## Commands Run
- `.venv/bin/python -m pytest tests/test_routes.py::test_user_form_contains_interactive_pet_controls tests/test_users.py`
  - Result: `28 passed`
- `.venv/bin/python -m pytest`
  - Result: `128 passed`
