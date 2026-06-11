# Assign ONLY Pets + Loading Flow

## Goal
- Add a per-user `Assign ONLY Pets` setting.
- Prevent long-running ForeKat and assignment actions from feeling frozen by showing an immediate loading page.

## Current Behavior
- Users can edit login, name, password, admin flag, active flag, and pets.
- Assignment generation always considers all active users for non-pet work.
- ForeKat test and assignment generation are synchronous actions with no intermediate loading UI.

## Desired Behavior
- Each user can be marked `Assign ONLY Pets`.
- Those users receive only their own valid in-pool pets.
- They never receive random hosts or prefix/sequence groups unless those hosts were already assigned to them as pets.
- Dashboard actions for ForeKat test and pool assignment show an immediate loading page with a spinner and auto-submit to the real POST action.

## Implementation Plan
1. Add `assign_only_pets` to `AppUser`, the user form, and the user templates.
2. Thread the flag through the assignment engine and exclude such users from non-pet assignment candidates.
3. Add a warning when every user is `Assign ONLY Pets` and non-pet hosts remain unassigned.
4. Add loading pages and update dashboard/action links to route through them.
5. Update tests for model defaults, form handling, assignment balancing, and the loading flow.

## Files Likely To Change
- `app/models.py`
- `app/forms.py`
- `app/users.py`
- `app/templates/user_form.html`
- `app/templates/users.html`
- `app/services/assignment_engine.py`
- `app/services/assignment_persistence.py`
- `app/main.py`
- `app/templates/dashboard.html`
- `app/templates/forekat_test.html`
- `app/templates/loading.html` (new)
- `app/static/js/loading_flow.js` (new)
- `app/static/styles.css`
- `migrations/versions/*`
- `tests/test_users.py`
- `tests/test_assignment.py`
- `tests/test_routes.py`
- `tests/test_assignment_persistence.py`

## Edge Cases
- A user marked `Assign ONLY Pets` still receives their pets if those pets are in the selected pool.
- Pets outside the selected pool stay unassigned and still warn as before.
- If all users are marked `Assign ONLY Pets`, non-pet hosts are left unassigned and a warning is emitted.
- The loading page must still work with JavaScript disabled via a visible continue button.

## Test / Verification Plan
- Run the assignment and route tests first, then the full pytest suite.
- Verify the loading page renders and auto-submits.
- Verify `assign_only_pets` is persisted and respected in assignment output.

## Progress Checklist
- [x] Inspect relevant code paths.
- [x] Record implementation plan.
- [x] Patch models, forms, routes, templates, engine, and migration.
- [x] Add/update tests.
- [x] Run targeted pytest and full pytest.

## Verification Notes
- Targeted test run: `69 passed`
- Full test run: `110 passed`
