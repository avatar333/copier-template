from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models import AppUser


@pytest.fixture
def app(tmp_path: Path):
    instance_path = tmp_path / "instance"
    instance_path.mkdir()
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = AppUser(login_name="admin", first_name="Admin", last_name="User", is_admin=True, is_active=True)
        admin.set_password("password123")
        regular = AppUser(login_name="regular", first_name="Regular", last_name="User", is_admin=False, is_active=True)
        regular.set_password("password123")
        db.session.add_all([admin, regular])
        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        return AppUser.query.filter_by(login_name="admin").first()


@pytest.fixture
def regular_user(app):
    with app.app_context():
        return AppUser.query.filter_by(login_name="regular").first()


def login(client, login_name: str, password: str = "password123"):
    return client.post(
        "/login",
        data={
            "login_name": login_name,
            "password": password,
        },
        follow_redirects=True,
    )
