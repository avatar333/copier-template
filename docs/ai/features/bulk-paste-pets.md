# Bulk Paste Pets

## Goal
- Allow users to paste multiple pet FQDNs into a pet entry box and add them with one `+` click.

## Current Behavior
- Each pet widget accepts one FQDN at a time.
- The entry control is a single-line input, so pasted line breaks are not reliable.

## Desired Behavior
- The Production and Non-Production pet widgets should accept one or more pasted FQDNs.
- Values should still be trimmed, lowercased, validated, deduplicated, and submitted through the existing hidden fields.

## Implementation Plan
1. Change the pet entry controls from single-line inputs to small textareas.
2. Update the existing JavaScript add handler to split pasted text on whitespace and common separators.
3. Keep widget-local add/remove behavior and hidden field syncing unchanged.
4. Run the relevant route and user tests.

## Files Likely To Change
- `app/templates/user_form.html`
- `app/static/js/user_form_pets.js`
- `app/static/styles.css`
- `tests/test_routes.py`

## Test / Verification Plan
- Run the user form route test.
- Run user CRUD tests to confirm hidden submitted values still save.

## Progress Checklist
- [x] Inspect current pet widget template, JavaScript, and styles.
- [x] Patch textarea and bulk add behavior.
- [x] Update tests.
- [x] Run relevant tests.

## Commands Run
- `.venv/bin/python -m pytest tests/test_routes.py::test_user_form_contains_interactive_pet_controls tests/test_users.py`
  - Result: `28 passed`
- `.venv/bin/python -m pytest`
  - Result: `128 passed`
