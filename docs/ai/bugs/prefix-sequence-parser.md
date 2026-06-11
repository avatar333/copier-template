# Prefix Sequence Parser Bug

## Goal

Fix prefix/sequence grouping so numeric suffixes can be detected on any hyphen-delimited hostname token, not only the first token.

## Current Behavior

The parser only recognizes `kafka01-stage-bry.platform.is`-style labels where the first token ends in two digits. Hostnames such as `apisix-docker01-prod-bry.platform.is` incorrectly fall through to random assignment.

## Desired Behavior

- Detect a two-digit numeric suffix on any hostname token
- Prefer the candidate token that yields the largest contiguous group
- If tied, prefer the leftmost candidate token
- Keep singleton or non-contiguous hosts in the random pool
- Preserve the existing `kafka01-stage-bry.platform.is` behavior

## Implementation Plan

1. Replace the first-token-only parser with a general token scanner.
2. Add deterministic candidate scoring across all possible numeric-suffix tokens.
3. Update the assignment engine to consume the new parser output.
4. Add regression tests for the `apisix-docker` and multi-candidate host cases.

## Files Likely To Change

- `app/services/assignment_helpers.py`
- `app/services/assignment_engine.py`
- `tests/test_grouping.py`
- `tests/test_assignment.py`
- `docs/ai/bugs/prefix-sequence-parser.md`

## Edge Cases

- Multiple numeric-suffix tokens in the same hostname label
- Non-contiguous sequence gaps
- Tied candidate scores
- Existing `kafka01-stage-bry.platform.is` hosts

## Test/Verification Plan

- Focused prefix grouping tests
- Assignment engine regression tests
- Full `pytest` run

## Progress Checklist

- [x] Inspect current parser and tests
- [x] Implement general token scanning
- [x] Add regression tests
- [x] Run focused and full pytest suites

## Verification

- `.venv/bin/python -m pytest tests/test_grouping.py tests/test_assignment.py` -> passed, 17 tests
- `.venv/bin/python -m compileall app tests run.py` -> passed
- `.venv/bin/python -m pytest` -> passed, 56 tests
