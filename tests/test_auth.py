from app.extensions import db
from app.models import AppUser
from conftest import login


def test_root_redirects_to_login_when_logged_out(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=%2Fdashboard")


def test_login_accepts_login_name(client):
    response = login(client, "admin")
    assert b"Dashboard" in response.data


def test_login_page_shows_create_admin_hint_when_no_users(client, app):
    with app.app_context():
        AppUser.query.delete()
        db.session.commit()

    response = client.get("/login")
    assert b"create-admin" in response.data
