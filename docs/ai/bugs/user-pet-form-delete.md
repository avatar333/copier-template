# User Pet Form And Delete Bug

## Goal

Replace the current pet-textarea workflow with an interactive add/remove pet list and fix user deletion so it succeeds for users with pets and historical assignments.

## Current Behavior

- User create/edit pages use an interactive add/remove pet list.
- The delete route now clears historical assignment references before deleting the user, but the underlying DB FK still needs to allow `NULL` for that to succeed.

## Desired Behavior

- A shared interactive pet list control on create/edit pages
- Server-side authoritative validation for pet FQDNs and duplicates
- User deletion that safely removes pets and preserves historical assignment rows
- Simple confirmation before deleting a user

## Implementation Plan

1. Update the form model to submit a hidden pet list plus a visible one-at-a-time add box.
2. Add a shared static JS helper for add/remove behavior and delete confirmation.
3. Update create/edit routes to validate and preserve submitted pets on failure.
4. Make user-owned pets cascade on delete and make assignment history user references nullable.
5. Add a migration for the FK change and update tests.

## Files Likely To Change

- `app/forms.py`
- `app/models.py`
- `app/users.py`
- `app/templates/user_form.html`
- `app/templates/users.html`
- `app/static/js/user_form_pets.js`
- `tests/test_users.py`
- `tests/conftest.py`
- `migrations/versions/*`
- `docs/ai/bugs/user-pet-form-delete.md`

## Edge Cases

- Duplicate pets in the same submission
- Duplicate pets already owned by another user
- Invalid pet FQDN input
- Validation failures that must preserve the submitted pet list
- Deleting a user with pets
- Deleting a user with historical assignments

## Test/Verification Plan

- Route tests for create/edit/delete behaviors
- Full `pytest` run

## Progress Checklist

- [x] Inspect current routes, forms, templates, and relationships
- [x] Implement interactive pet list UI
- [x] Fix delete cascade/reference handling
- [x] Add/update tests
- [x] Run pytest

## Verification

- `.venv/bin/python -m pytest tests/test_users.py tests/test_routes.py` -> `28 passed`
- `.venv/bin/python -m pytest` -> `68 passed`
