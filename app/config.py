from __future__ import annotations

from pathlib import Path
import secrets
from typing import Any
from urllib.parse import quote, unquote, urlparse

import yaml
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError


CONFIG_PATH = Path("config.yaml")
DB_DETAILS_PATH = Path("db_details.txt")
PAT_PATH = Path("pat.txt")

TODO_DATABASE = {
    "host": "TODO_DATABASE_HOST",
    "port": 3306,
    "name": "TODO_DATABASE_NAME",
    "username": "TODO_DATABASE_USERNAME",
    "password": "TODO_DATABASE_PASSWORD",
}
TODO_FOREKAT_USERNAME = "TODO_FOREMAN_USERNAME"
TODO_FOREKAT_PAT = "TODO_FOREMAN_PAT"


class ConfigError(RuntimeError):
    pass


def load_config(
    config_path: str | Path = CONFIG_PATH,
    *,
    bootstrap_missing: bool = True,
) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        if not bootstrap_missing:
            raise ConfigError(f"Configuration file {path} does not exist.")
        ensure_config_yaml(config_path=path)

    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Configuration file {path} must contain a YAML mapping.")

    database_cfg = raw.get("database")
    if isinstance(database_cfg, dict):
        raw["database"] = _normalize_db_mapping(database_cfg)

    assignment_cfg = raw.setdefault("assignment", {})
    if isinstance(assignment_cfg, dict):
        assignment_cfg.setdefault("random_seed", None)
        assignment_cfg.setdefault("min_prefix_group_size", 2)
        assignment_cfg.setdefault("prefix_group_randomness_window", 1)

    validate_config(raw)
    return raw


def validate_config(config: dict[str, Any]) -> None:
    missing_sections = [section for section in ("app", "database", "forekat", "assignment") if section not in config]
    if missing_sections:
        raise ConfigError(
            "config.yaml is missing required sections: " + ", ".join(missing_sections)
        )

    app_cfg = _mapping(config["app"], "app")
    db_cfg = _mapping(config["database"], "database")
    forekat_cfg = _mapping(config["forekat"], "forekat")
    assignment_cfg = _mapping(config["assignment"], "assignment")

    missing_values: list[str] = []
    placeholder_values: list[str] = []

    for path, value in (
        ("app.secret_key", app_cfg.get("secret_key")),
        ("database.host", db_cfg.get("host")),
        ("database.port", db_cfg.get("port")),
        ("database.name", db_cfg.get("name")),
        ("database.username", db_cfg.get("username")),
        ("database.password", db_cfg.get("password")),
        ("database.sqlalchemy_uri", db_cfg.get("sqlalchemy_uri")),
        ("forekat.foreman_api_url", forekat_cfg.get("foreman_api_url")),
        ("forekat.katello_api_url", forekat_cfg.get("katello_api_url")),
        ("forekat.username", forekat_cfg.get("username")),
        ("forekat.personal_access_token", forekat_cfg.get("personal_access_token")),
        ("forekat.timeout_seconds", forekat_cfg.get("timeout_seconds")),
        ("assignment.min_prefix_group_size", assignment_cfg.get("min_prefix_group_size")),
        ("assignment.prefix_group_randomness_window", assignment_cfg.get("prefix_group_randomness_window")),
    ):
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_values.append(path)
        elif isinstance(value, str) and value.startswith("TODO_"):
            placeholder_values.append(path)

    if missing_values:
        raise ConfigError(
            "config.yaml is missing required values: " + ", ".join(sorted(missing_values))
        )

    if placeholder_values:
        raise ConfigError(
            "config.yaml still contains TODO placeholders for: "
            + ", ".join(sorted(placeholder_values))
        )

    sqlalchemy_uri = str(db_cfg.get("sqlalchemy_uri", ""))
    if sqlalchemy_uri and not sqlalchemy_uri.startswith("mysql+pymysql://"):
        raise ConfigError("database.sqlalchemy_uri must use the mysql+pymysql dialect.")


def ensure_config_yaml(
    config_path: str | Path = CONFIG_PATH,
    db_details_path: str | Path = DB_DETAILS_PATH,
    pat_path: str | Path = PAT_PATH,
    *,
    overwrite: bool = False,
) -> Path:
    path = Path(config_path)
    if path.exists() and not overwrite:
        return path
    config_data = build_config_dict(
        db_details_path=Path(db_details_path),
        pat_path=Path(pat_path),
    )
    path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    return path


def build_config_dict(
    db_details_path: Path = DB_DETAILS_PATH,
    pat_path: Path = PAT_PATH,
) -> dict[str, Any]:
    db_config = _build_database_config(db_details_path)
    forekat_username, forekat_pat = _build_forekat_auth(pat_path)
    return {
        "app": {
            "secret_key": secrets.token_urlsafe(32),
            "debug": False,
            "session_cookie_secure": False,
        },
        "database": db_config,
        "forekat": {
            "foreman_api_url": "https://forekat-prod.platform.is/api",
            "katello_api_url": "https://forekat-prod.platform.is/katello/api",
            "username": forekat_username,
            "personal_access_token": forekat_pat,
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


def _build_database_config(db_details_path: Path) -> dict[str, Any]:
    parsed = _parse_db_details(db_details_path)
    host = parsed.get("host") or TODO_DATABASE["host"]
    port = int(parsed.get("port") or TODO_DATABASE["port"])
    name = parsed.get("name") or TODO_DATABASE["name"]
    username = parsed.get("username") or TODO_DATABASE["username"]
    password = parsed.get("password") or TODO_DATABASE["password"]
    sqlalchemy_uri = parsed.get("sqlalchemy_uri") or _compose_sqlalchemy_uri(
        host=host,
        port=port,
        name=name,
        username=username,
        password=password,
    )
    return {
        "host": host,
        "port": port,
        "name": name,
        "username": username,
        "password": password,
        "sqlalchemy_uri": sqlalchemy_uri,
    }


def _build_forekat_auth(pat_path: Path) -> tuple[str, str]:
    parsed = _parse_pat_details(pat_path)
    username = parsed.get("username") or TODO_FOREKAT_USERNAME
    personal_access_token = parsed.get("personal_access_token") or TODO_FOREKAT_PAT
    return username, personal_access_token


def _parse_db_details(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}

    direct_uri = _parse_uri_line(text)
    if direct_uri:
        return direct_uri

    yaml_like = yaml.safe_load(text)
    if isinstance(yaml_like, dict):
        return _normalize_db_mapping(yaml_like)

    parsed: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "://" in stripped and "=" not in stripped and ":" not in stripped.split("://", 1)[0]:
            uri_data = _parse_uri_line(stripped)
            if uri_data:
                return uri_data
        separator = ":" if ":" in stripped else "=" if "=" in stripped else None
        if not separator:
            continue
        key, value = stripped.split(separator, 1)
        parsed[key.strip()] = value.strip()

    return _normalize_db_mapping(parsed)


def _parse_pat_details(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}

    yaml_like = yaml.safe_load(text)
    if isinstance(yaml_like, dict):
        return _normalize_pat_mapping(yaml_like)

    parsed: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        separator = ":" if ":" in stripped else "=" if "=" in stripped else None
        if separator:
            key, value = stripped.split(separator, 1)
            parsed[key.strip()] = value.strip()
        elif "personal_access_token" not in parsed:
            parsed["personal_access_token"] = stripped

    normalized = _normalize_pat_mapping(parsed)
    if normalized:
        return normalized

    return {"personal_access_token": text}


def _normalize_db_mapping(data: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    aliases = {
        "vip": "host",
        "host": "host",
        "hostname": "host",
        "server": "host",
        "db_name": "name",
        "database": "name",
        "database_name": "name",
        "name": "name",
        "username": "username",
        "user": "username",
        "password": "password",
        "pass": "password",
        "port": "port",
        "sqlalchemy_uri": "sqlalchemy_uri",
        "database_uri": "sqlalchemy_uri",
        "db_uri": "sqlalchemy_uri",
        "uri": "sqlalchemy_uri",
    }

    for raw_key, raw_value in data.items():
        key = aliases.get(str(raw_key).strip().lower())
        if not key:
            continue
        value = str(raw_value).strip()
        if value:
            normalized[key] = value

    if "sqlalchemy_uri" in normalized:
        uri_data = _parse_sqlalchemy_uri(normalized["sqlalchemy_uri"])
        normalized = {**normalized, **uri_data}

    return normalized


def _normalize_pat_mapping(data: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    aliases = {
        "username": "username",
        "user": "username",
        "token": "personal_access_token",
        "pat": "personal_access_token",
        "pat_token": "personal_access_token",
        "personal_access_token": "personal_access_token",
    }
    for raw_key, raw_value in data.items():
        key = aliases.get(str(raw_key).strip().lower())
        if not key:
            continue
        value = str(raw_value).strip()
        if value:
            normalized[key] = value
    return normalized


def _parse_uri_line(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith(("mysql://", "mysql+pymysql://", "mariadb://")):
        return _parse_sqlalchemy_uri(stripped)
    return None


def _parse_sqlalchemy_uri(uri: str) -> dict[str, Any]:
    parsed = urlparse(uri.replace("mariadb://", "mysql+pymysql://", 1))
    if not parsed.hostname or not parsed.path:
        return {"sqlalchemy_uri": uri}
    name = parsed.path.lstrip("/")
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "name": name,
        "username": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "sqlalchemy_uri": _compose_sqlalchemy_uri(
            host=parsed.hostname,
            port=parsed.port or 3306,
            name=name,
            username=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
        ),
    }


def _compose_sqlalchemy_uri(
    *,
    host: str,
    port: int,
    name: str,
    username: str,
    password: str,
) -> str:
    if any(str(value).startswith("TODO_") for value in (host, name, username, password)):
        return "TODO_SQLALCHEMY_URI"
    return (
        f"mysql+pymysql://{quote(username)}:{quote(password)}"
        f"@{host}:{port}/{name}?charset=utf8mb4"
    )


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must be a YAML mapping.")
    return value


def load_settings(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    return load_config(config_path)


def validate_settings(config: dict[str, Any]) -> None:
    validate_config(config)


def validate_database_connection(sqlalchemy_uri: str) -> None:
    engine = create_engine(sqlalchemy_uri, pool_pre_ping=True)
    try:
        with engine.connect():
            return
    except SQLAlchemyError as exc:
        raise ConfigError("Database connection failed.") from exc
    finally:
        engine.dispose()
