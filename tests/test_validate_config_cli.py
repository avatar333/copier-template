from __future__ import annotations

from pathlib import Path

from app import create_app


def _valid_config() -> dict:
    return {
        "app": {
            "secret_key": "abc123",
            "debug": False,
            "session_cookie_secure": False,
        },
        "database": {
            "host": "db.internal",
            "port": 3306,
            "name": "forekat",
            "username": "dbuser",
            "password": "dbpass",
            "sqlalchemy_uri": "mysql+pymysql://dbuser:dbpass@db.internal:3306/forekat?charset=utf8mb4",
        },
        "forekat": {
            "foreman_api_url": "https://forekat.example/api",
            "katello_api_url": "https://forekat.example/katello/api",
            "username": "foreman-user",
            "personal_access_token": "token-value",
            "verify_ssl": True,
            "ca_bundle": None,
            "timeout_seconds": 30,
            "host_search": "",
        },
        "assignment": {
            "random_seed": None,
            "min_prefix_group_size": 2,
            "prefix_group_randomness_window": 1,
        },
    }


def test_validate_config_command_succeeds_without_forekat(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.factory.ensure_config_yaml", lambda *args, **kwargs: Path("config.yaml"))
    monkeypatch.setattr("app.factory.load_config", lambda *args, **kwargs: _valid_config())
    monkeypatch.setattr("app.factory.validate_database_connection", lambda *args, **kwargs: None)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        }
    )
    runner = app.test_cli_runner()
    result = runner.invoke(args=["validate-config"])

    assert result.exit_code == 0
    assert "Configuration is valid." in result.output


def test_validate_config_command_succeeds_with_forekat(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.factory.ensure_config_yaml", lambda *args, **kwargs: Path("config.yaml"))
    monkeypatch.setattr("app.factory.load_config", lambda *args, **kwargs: _valid_config())
    monkeypatch.setattr("app.factory.validate_database_connection", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.factory.ForeKatClient.check_status", lambda self: {"status": "ok"})

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        }
    )
    runner = app.test_cli_runner()
    result = runner.invoke(args=["validate-config", "--forekat"])

    assert result.exit_code == 0
    assert "Configuration is valid." in result.output


def test_validate_config_command_rejects_placeholder_username(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.factory.ensure_config_yaml", lambda *args, **kwargs: Path("config.yaml"))

    config = _valid_config()
    config["forekat"]["username"] = "TODO_FOREMAN_USERNAME"
    monkeypatch.setattr("app.factory.load_config", lambda *args, **kwargs: config)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        }
    )
    runner = app.test_cli_runner()
    result = runner.invoke(args=["validate-config"])

    assert result.exit_code != 0
    assert "forekat.username" in result.output
    assert "TODO_FOREMAN_USERNAME" not in result.output
