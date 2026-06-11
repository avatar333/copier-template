from __future__ import annotations

import click
from pathlib import Path
import sys
from flask import Flask

from .auth import auth_bp
from .config import (
    CONFIG_PATH,
    ConfigError,
    ensure_config_yaml,
    load_config,
    validate_database_connection,
    validate_config,
)
from .extensions import csrf, db, login_manager, migrate
from .main import main_bp
from .models import AppUser
from .services.forekat_client import ForeKatClient, ForeKatClientError
from .users import users_bp


def create_app(test_config: dict | None = None) -> Flask:
    if "validate-config" not in sys.argv:
        ensure_config_yaml()
    config = load_config()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config["app"]["secret_key"],
        DEBUG=bool(config["app"].get("debug", False)),
        SESSION_COOKIE_SECURE=bool(config["app"].get("session_cookie_secure", False)),
        SQLALCHEMY_DATABASE_URI=config["database"]["sqlalchemy_uri"],
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)
    app.forekat_config = config["forekat"]
    app.assignment_config = config["assignment"]

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(users_bp)

    register_cli(app)
    return app


def register_cli(app: Flask) -> None:
    def _create_admin(login_name: str, first_name: str, last_name: str, password: str) -> None:
        normalized_login_name = login_name.strip().lower()
        existing = AppUser.query.filter_by(login_name=normalized_login_name).first()
        if existing:
            raise click.ClickException("That login name already exists.")

        user = AppUser(
            login_name=normalized_login_name,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            is_admin=True,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Admin user created.")

    @app.cli.command("create-admin")
    @click.option("--login-name", required=True)
    @click.option("--first-name", required=True)
    @click.option("--last-name", required=True)
    @click.option("--password", required=True)
    def create_admin(login_name: str, first_name: str, last_name: str, password: str) -> None:
        _create_admin(login_name, first_name, last_name, password)

    @app.cli.command("init-admin")
    @click.option("--login-name", required=True)
    @click.option("--first-name", required=True)
    @click.option("--last-name", required=True)
    @click.option("--password", required=True)
    def init_admin(login_name: str, first_name: str, last_name: str, password: str) -> None:
        _create_admin(login_name, first_name, last_name, password)

    @app.cli.command("validate-config")
    @click.option("--forekat", is_flag=True, help="Also validate ForeKat /status.")
    def validate_config_command(forekat: bool) -> None:
        if not Path(CONFIG_PATH).exists():
            raise click.ClickException("config.yaml does not exist. Create it before running validation.")

        try:
            config = load_config(CONFIG_PATH, bootstrap_missing=False)
            validate_config(config)
            validate_database_connection(config["database"]["sqlalchemy_uri"])
        except ConfigError as exc:
            raise click.ClickException(str(exc)) from exc

        if forekat:
            try:
                client = ForeKatClient(config["forekat"])
                client.check_status()
            except ForeKatClientError as exc:
                raise click.ClickException(f"ForeKat /status validation failed: {exc}") from exc

        click.echo("Configuration is valid.")
