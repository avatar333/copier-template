# Documentation Page

## Goal

Add a left-navigation `Documentation` button that opens a thorough in-app explanation of the app’s behavior, especially the assignment rules.

## Current behavior

- The sidebar has links for Dashboard, Available Hosts, Pets, Latest Assignment, ForeKat Test, and user management.
- No dedicated in-app documentation page exists.

## Desired behavior

- Add a `Documentation` button in the left sidebar.
- Create a logged-in documentation page that explains:
  - host pool selection
  - exclusions
  - pets-first behavior
  - prefix-sequence grouping logic
  - special JBoss groups
  - `Assign ONLY Pets`
  - loading flow and export behavior where relevant

## Implementation plan

1. Add a `/documentation` route.
2. Add a documentation template with detailed, accurate sections.
3. Add a sidebar link with a book-style icon.
4. Add route tests for access control and content.
5. Verify the final diff and test suite.

## Files likely to change

- `app/main.py`
- `app/templates/base.html`
- `app/templates/documentation.html`
- `tests/test_routes.py`
- `README.md` if a brief pointer is needed

## Edge cases

- The page should be readable and not overclaim behavior not present in code.
- The page should remain accessible to any logged-in user.

## Verification plan

- `python -m pytest tests/test_routes.py -q`
- `python -m pytest`

## Progress

- [x] Add planning note
- [ ] Add route and template
- [ ] Add sidebar link
- [ ] Add tests
- [ ] Verify
