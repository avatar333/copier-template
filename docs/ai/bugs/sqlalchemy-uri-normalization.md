# SQLAlchemy URI Normalization

## Goal

Prevent startup failures when `config.yaml` contains a MySQL/MariaDB database URI in a supported but non-driver-specific form such as `mysql://` or `mariadb://`.

## Current behavior

- `load_config()` validates that `database.sqlalchemy_uri` uses the `mysql+pymysql` dialect.
- Runtime configs that still use `mysql://` or `mariadb://` can cause the app to fail during Gunicorn startup.

## Desired behavior

- Normalize supported MySQL-style URIs to `mysql+pymysql://` when loading configuration.
- Keep rejecting unrelated or malformed database URIs.

## Implementation plan

1. Normalize the loaded `database` section before validation.
2. Keep the strict validation for the final SQLAlchemy URI.
3. Add regression tests for `mysql://` and `mariadb://`.
4. Document the accepted runtime URI forms in the README.

## Files likely to change

- `app/config.py`
- `tests/test_config.py`
- `README.md`

## Edge cases

- Placeholder values should still fail validation.
- The app must keep using the `mysql+pymysql` driver internally even if the input URI was `mysql://` or `mariadb://`.

## Verification plan

- Run the config tests.
- Run the full test suite.

## Progress

- [x] Add planning note
- [x] Implement normalization
- [x] Add regression tests
- [x] Update README
- [x] Verify tests and diff

## Verification

- `.venv/bin/python -m pytest tests/test_config.py tests/test_config_parsing.py -q` -> `5 passed`
- `.venv/bin/python -m pytest` -> `158 passed`
