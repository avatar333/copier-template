# [[ project_name ]]

This is a Copier template for a Flask UI starter with the same dark-blue shell, cards, sidebar, and loading flow as the original snapshot.

## Template Variables

- `project_name`: Human-readable application name used in titles and headings.
- `project_slug`: Slug for the generated repository or package name.
- `route_host`: Hostname or host:port where the generated app will be served.
- `namespace`: Flask blueprint namespace used in `url_for()` and endpoint checks.

## How To Use It

1. Install Copier if you do not already have it.
2. Render the template into a new directory:

   ```bash
   copier copy path/to/copier-template path/to/new-project \
     --data project_name="My Admin" \
     --data project_slug="my-admin" \
     --data route_host="localhost:5000" \
     --data namespace="main"
   ```

3. Initialize the rendered output as its own git repository if needed.
4. Wire the templates into your Flask app or equivalent backend.
5. Keep `app/templates/base.html` and `app/static/styles.css` as the visual source of truth.

## What This Template Includes

- Shared dark-blue dashboard styling
- Sidebar, card, table, and loading-page layout
- Responsive page shell and reusable template structure
- Documentation page styling and content patterns
- Login-page presentation

## What This Template Excludes

- Backend services specific to any previous project
- Database models or migrations
- Assignment generation logic
- Export logic
- OpenShift manifests or runtime bootstrap code

## Design Notes

- The shared shell lives in `app/templates/base.html`.
- The visual system lives in `app/static/styles.css`.
- Loading behavior is driven by `app/templates/loading.html` and `app/static/js/loading_action.js`.
- The documentation page is provided as an example of the same visual system applied to a content-heavy page.

## Where To Start

- Read `CONTEXT.md` for the design handoff summary.
- Start from `app/templates/base.html` and `app/static/styles.css` if you want the same UI feel in a new feature.
- Use `app/templates/login.html`, `dashboard.html`, and `loading.html` as examples of the common page patterns.
