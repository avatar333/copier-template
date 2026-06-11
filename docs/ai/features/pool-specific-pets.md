# Pool-Specific Pets

## Goal
- Split each user's pets into `Production Pets` and `Non-Production Pets`.
- Ensure each pet list only affects assignment generation for its matching host pool.

## Current Behavior
- `PetHost` stores only a single untyped FQDN per row.
- User create/edit has one pet list and one hidden submitted blob.
- Assignment persistence loads every pet and uses the selected host pool only as an inventory membership filter.
- Assignment pages and the pets summary page show a single pet list per user.

## Desired Behavior
- Each pet is typed as `production` or `non_production`.
- User create/edit presents two independent pet widgets.
- Production assignments use only `production` pets.
- Non-Production assignments use only `non_production` pets.
- `Assign ONLY Pets` continues to work, but only with the selected pool's pets.

## Implementation Plan
1. Add `pet_type` to `PetHost` with a safe backfill.
2. Replace the single pet form field with `production_pet_blob` and `non_production_pet_blob`.
3. Generalize the pet widget JS to support multiple independent lists per form.
4. Update user CRUD, pets summary, and users list to show both pet categories.
5. Update assignment persistence and result rendering to use the selected pool's pets only.
6. Update tests for model constraints, form behavior, assignment behavior, and route output.

## Files Likely To Change
- `app/models.py`
- `app/forms.py`
- `app/users.py`
- `app/main.py`
- `app/services/assignment_persistence.py`
- `app/services/assignment_engine.py`
- `app/static/js/user_form_pets.js`
- `app/templates/user_form.html`
- `app/templates/users.html`
- `app/templates/pets.html`
- `app/templates/assignments.html`
- `migrations/versions/*`
- `tests/test_users.py`
- `tests/test_assignment.py`
- `tests/test_assignment_persistence.py`
- `tests/test_routes.py`

## Edge Cases
- The same FQDN may exist once as a Production Pet and once as a Non-Production Pet.
- The same FQDN must not be assigned to two different users for the same pet type.
- Historical assignment runs must stay readable.
- Legacy pets need a conservative backfill choice that minimizes unintended Production pet priority.

## Decisions
- Backfill existing untyped pets to `non_production`.
  This is the conservative choice because it avoids silently granting pet priority in Production runs for legacy data.

## Test / Verification Plan
- Run targeted tests for users, assignment persistence, routes, and assignment engine.
- Run the full pytest suite after the targeted passes.

## Progress Checklist
- [x] Inspect current model, routes, UI, assignment code, and tests.
- [x] Record the design and backfill choice.
- [x] Patch model, migration, forms, JS, routes, and templates.
- [x] Patch assignment persistence and result display.
- [x] Add and update tests.
- [x] Run `.venv/bin/python -m pytest`.

## Commands Run
- `.venv/bin/python -m pytest tests/test_users.py tests/test_assignment_persistence.py tests/test_routes.py`
  - Result: `51 passed`
- `.venv/bin/python -m pytest`
  - Result: `119 passed`
