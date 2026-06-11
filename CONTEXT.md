# Context Handoff

This file preserves the design and implementation context that began with the prompt:

> I really like the page layout and the CSS used. How would you supply a reusable framework and in what form, so that I can have a drop-in suite I can place in an empty project directory and develop a site with all this context available for the same look and feel?

## Conversation Timeline

1. Reusable framework option:
   - A copyable starter repository was recommended instead of a library.
   - `Copier` was chosen as the best long-lived template mechanism.
2. Handoff packaging:
   - You asked to put the starter in a subdirectory here so it could be copied to a new location, turned into a git repository, and continued in a new chat.
   - The first snapshot included the full ForeKat app, but you later narrowed the requirement to the UI framework only.
3. UI framework scope:
   - Keep the dark-blue dashboard and sidebar layout.
   - Keep the loading page pattern and centered spinner behavior.
   - Keep the documentation page as an example of the same visual system applied to explanatory content.
   - Keep the reusable template shell and stylesheet.
   - Exclude backend, deployment, database, and ForeKat-specific logic from the starter snapshot.
4. Operational context:
   - The starter should be easy to copy into a new directory and initialized as a fresh git project.
   - The resulting project should use the included templates and stylesheet as the visual source of truth.

## Summary Of The Decisions

1. The reusable framework should be a copyable starter repository rather than a library.
2. `Copier` is the preferred template mechanism when the starter needs to be kept up to date over time.
3. The starter should include:
   - a shared `base.html`
   - the dark blue theme in `styles.css`
   - loading-page behavior
   - a dashboard shell
   - the documentation page
   - the login page
4. A `CONTEXT.md` file should preserve the design and operational decisions from this conversation.
5. The starter should be easy to copy into a new directory, then initialized as a fresh git project.

## Key Follow-Up Decisions

- The `Documentation` page was added to the sidebar to show how the same UI shell handles rich instructional content.
- The loading page was simplified to a centered spinner and auto-submit flow.
- The template should remain focused on presentation-layer reuse, not the ForeKat backend.
- The included files should be treated as a visual starter, not a running application by themselves.

## Important Runtime Notes

- There are no runtime secrets or deployment assumptions in the trimmed starter.
- Any new project using this starter will need its own backend wiring and configuration.

## What To Carry Into The New Repository

- The template README
- The layout and CSS in `app/templates/base.html` and `app/static/styles.css`
- The loading flow
- The documentation page
- The login page

## Next Chat Seed

When continuing in a new chat, point Codex at the copied starter directory and say that this is the reusable Copier-style UI scaffold built from the ForeKat Admin look and feel.
