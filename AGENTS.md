# AGENTS.md

This file gives Codex persistent project guidance. Follow it for all work in this repository.

## Project overview

<!-- Replace this section for each project. Keep it short and concrete. -->

- Project name: TODO
- Purpose: TODO
- Primary language/framework: TODO
- Runtime/platform: TODO
- Package manager: TODO
- Main entry points:
  - TODO
- Important directories:
  - `src/` - TODO
  - `tests/` - TODO
  - `docs/` - TODO
  - `scripts/` - TODO

## Core working principles

- Prefer small, focused changes over large rewrites.
- Preserve existing behavior unless the task explicitly asks to change it.
- Read the relevant code before proposing changes.
- Do not invent architecture, APIs, commands, environment variables, or file paths.
- When uncertain, inspect the repository first, then make a reasonable, minimal assumption.
- Optimize for maintainability, readability, and testability.
- Keep public interfaces stable unless the requested change requires otherwise.
- Do not add new dependencies without a clear reason.

## AI workflow for features and fixes

For non-trivial work, use a lightweight spec-first workflow.

1. Create or update a Markdown note under `docs/ai/` before implementing:
   - Features: `docs/ai/features/<feature-name>.md`
   - Bugs: `docs/ai/bugs/<bug-name>.md`
   - Refactors: `docs/ai/refactors/<refactor-name>.md`

2. The note should include:
   - Goal
   - Current behavior
   - Desired behavior
   - Implementation plan
   - Files likely to change
   - Edge cases
   - Test/verification plan
   - Progress checklist

3. During implementation:
   - Keep the note updated when the plan changes.
   - Mark completed steps.
   - Record important decisions.
   - Record commands run and their results.

4. At the end:
   - Summarize what changed.
   - List tests/checks run.
   - Mention any known limitations or follow-up work.

Skip the Markdown note only for very small changes such as typo fixes, simple renames, or obvious one-line corrections.

## Repository safety rules

- Do not delete files or large blocks of code unless the task explicitly requires it.
- Do not run destructive commands such as:
  - `rm -rf`
  - `git reset --hard`
  - `git clean -fd`
  - database reset/drop commands
  - production deployment commands
- Do not modify secrets, credentials, tokens, private keys, or `.env` files unless explicitly instructed.
- Do not print secrets in logs or responses.
- Do not make network calls, install packages, or change lockfiles unless needed for the task.
- Ask before introducing a new production dependency.
- Prefer editing existing files over creating new abstractions prematurely.

## Coding standards

- Match the style of the existing codebase.
- Prefer clear names over clever names.
- Keep functions small and cohesive.
- Avoid unnecessary abstraction.
- Handle errors explicitly.
- Validate inputs at system boundaries.
- Keep business logic separate from transport/UI/framework glue where practical.
- Add comments only when they explain why something is done, not what obvious code does.
- Update documentation when behavior, commands, or configuration change.

## Testing and verification

Before marking work complete, run the smallest relevant verification first, then broader checks when appropriate.

Project commands:

```sh
# Install dependencies
TODO

# Run tests
TODO

# Run linting
TODO

# Run type checks
TODO

# Run formatting
TODO

# Build
TODO

# Run locally
TODO
