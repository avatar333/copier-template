from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ConfigError, load_config


def test_load_config_rejects_placeholder_username(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  secret_key: "abc"
  debug: false
  session_cookie_secure: false
database:
  host: "db"
  port: 3306
  name: "name"
  username: "user"
  password: "pass"
  sqlalchemy_uri: "mysql+pymysql://user:pass@db:3306/name?charset=utf8mb4"
forekat:
  foreman_api_url: "https://example/api"
  katello_api_url: "https://example/katello/api"
  username: "TODO_FOREMAN_USERNAME"
  personal_access_token: "token"
  verify_ssl: true
  ca_bundle: null
  timeout_seconds: 30
  host_search: ""
assignment:
  random_seed: null
  min_prefix_group_size: 2
  prefix_group_randomness_window: 1
"""
    )

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_load_config_reports_placeholder_before_sqlalchemy_dialect(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  secret_key: "abc"
  debug: false
  session_cookie_secure: false
database:
  host: "TODO_DATABASE_HOST"
  port: 3306
  name: "TODO_DATABASE_NAME"
  username: "TODO_DATABASE_USERNAME"
  password: "TODO_DATABASE_PASSWORD"
  sqlalchemy_uri: "TODO_SQLALCHEMY_URI"
forekat:
  foreman_api_url: "https://example/api"
  katello_api_url: "https://example/katello/api"
  username: "user"
  personal_access_token: "token"
  verify_ssl: true
  ca_bundle: null
  timeout_seconds: 30
  host_search: ""
assignment:
  random_seed: null
  min_prefix_group_size: 2
  prefix_group_randomness_window: 1
"""
    )

    with pytest.raises(ConfigError, match="TODO placeholders"):
        load_config(config_path)


@pytest.mark.parametrize(
    ("sqlalchemy_uri", "expected_prefix"),
    [
        ("mysql://user:pass@db:3306/name?charset=utf8mb4", "mysql+pymysql://"),
        ("mariadb://user:pass@db:3306/name?charset=utf8mb4", "mysql+pymysql://"),
    ],
)
def test_load_config_normalizes_mysql_style_sqlalchemy_uri(
    tmp_path: Path,
    sqlalchemy_uri: str,
    expected_prefix: str,
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  secret_key: "abc"
  debug: false
  session_cookie_secure: false
database:
  sqlalchemy_uri: "{sqlalchemy_uri}"
forekat:
  foreman_api_url: "https://example/api"
  katello_api_url: "https://example/katello/api"
  username: "user"
  personal_access_token: "token"
  verify_ssl: true
  ca_bundle: null
  timeout_seconds: 30
  host_search: ""
assignment:
  random_seed: null
  min_prefix_group_size: 2
  prefix_group_randomness_window: 1
"""
    )

    config = load_config(config_path)

    assert config["database"]["sqlalchemy_uri"].startswith(expected_prefix)
