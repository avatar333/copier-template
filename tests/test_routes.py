from __future__ import annotations

from pathlib import Path
from datetime import date
from types import SimpleNamespace

from app import create_app
from app.extensions import db
from app.main import _build_assignment_detail
from app.models import AppUser, AssignmentRun, HostAssignment, HostExclusion, PetHost
from app.services.exporter import ExportZipResult
from conftest import login


def test_hosts_requires_login(client):
    response = client.get("/hosts", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=%2Fhosts")


def test_host_exclusions_requires_login(client):
    response = client.get("/hosts/exclusions", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=%2Fhosts%2Fexclusions")


def test_pets_requires_login(client):
    response = client.get("/pets", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=%2Fpets")


def test_documentation_requires_login(client):
    response = client.get("/documentation", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=%2Fdocumentation")


def test_latest_assignment_redirects_to_newest_run(client, app):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(host_count=3, user_count=2)
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    response = client.get("/assignments/latest", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/assignments/{run_id}")


def test_generate_assignments_redirects_to_created_run(client, monkeypatch):
    login(client, "admin")

    def fake_snapshot(_client):
        return {
            "all_hosts": [
                {"id": 1, "fqdn": "pet01.example.com"},
                {"id": 2, "fqdn": "db01.example.com"},
                {"id": 3, "fqdn": "db02.example.com"},
            ],
            "warnings": [],
        }

    monkeypatch.setattr("app.services.assignment_persistence.get_inventory_snapshot", fake_snapshot)

    response = client.post("/assignments/generate", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/assignments/1")
    with client.application.app_context():
        assert AssignmentRun.query.count() == 1


def test_generate_assignments_pool_routes_pass_selected_pool(client, monkeypatch):
    login(client, "admin")
    called_pools: list[str | None] = []

    class FakeRun:
        id = 42

    def fake_generate(current_user_id, pool_name=None, client=None, rng=None):
        called_pools.append(pool_name)
        return FakeRun()

    monkeypatch.setattr("app.main.generate_and_persist_assignment", fake_generate)

    production_response = client.post("/assignments/generate/production", follow_redirects=False)
    non_production_response = client.post("/assignments/generate/non-production", follow_redirects=False)

    assert production_response.status_code == 302
    assert production_response.headers["Location"].endswith("/assignments/42")
    assert non_production_response.status_code == 302
    assert non_production_response.headers["Location"].endswith("/assignments/42")
    assert called_pools == ["production", "non_production"]


def test_assignment_generate_get_shows_loading_page(client):
    login(client, "admin")

    response = client.get("/assignments/generate/production")

    assert response.status_code == 200
    assert b"Retrieving data and generating the production host assignment..." in response.data
    assert b"Continue to generate Production hosts assignment" not in response.data
    assert b'data-loading-action-form' in response.data
    assert b'loading-spinner' in response.data


def test_generate_assignments_requires_admin(client):
    login(client, "regular")

    response = client.post("/assignments/generate", follow_redirects=False)

    assert response.status_code == 403


def test_assignment_generate_loading_route_requires_admin(client):
    login(client, "regular")

    response = client.get("/assignments/generate/production", follow_redirects=False)

    assert response.status_code == 403


def test_hosts_page_does_not_display_host_collection_information(client):
    login(client, "admin")
    response = client.get("/hosts")

    assert response.status_code == 200
    assert b"Host Collections" not in response.data


def test_hosts_page_shows_total_hosts_after_refresh(client, monkeypatch):
    login(client, "admin")

    def fake_inventory(_client):
        return {
            "all_hosts": [
                {"id": 1, "fqdn": "host01.example.com"},
                {"id": 2, "fqdn": "host02.example.com"},
            ],
            "warnings": [],
        }

    monkeypatch.setattr("app.main.get_inventory_snapshot", fake_inventory)

    response = client.post("/hosts")

    assert response.status_code == 200
    assert b"Available Hosts" in response.data
    assert b"Total Hosts: 2" in response.data
    assert b"host01.example.com" in response.data
    assert b"host02.example.com" in response.data


def test_host_exclusions_page_is_viewable_by_logged_in_users(client):
    login(client, "regular")
    response = client.get("/hosts/exclusions")

    assert response.status_code == 200
    assert b"Host Exclusions List" in response.data
    assert b"Editing is restricted to administrators." in response.data
    assert b"Save" not in response.data


def test_host_exclusions_page_shows_current_values(client, app):
    login(client, "admin")
    with app.app_context():
        db.session.add_all(
            [
                HostExclusion(fqdn="host01.example.com"),
                HostExclusion(fqdn="host02.example.com"),
            ]
        )
        db.session.commit()

    response = client.get("/hosts/exclusions")

    assert response.status_code == 200
    assert b"host01.example.com" in response.data
    assert b"host02.example.com" in response.data


def test_non_admin_cannot_save_host_exclusions(client):
    login(client, "regular")
    response = client.post(
        "/hosts/exclusions",
        data={"host_exclusions": "host01.example.com"},
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_admin_can_save_host_exclusions_with_normalization_and_deduplication(client, app):
    login(client, "admin")
    response = client.post(
        "/hosts/exclusions",
        data={
            "host_exclusions": " HOST01.EXAMPLE.COM \n\nhost02.example.com\nHOST01.example.com\n",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Saved 2 host exclusion(s)." in response.data
    with app.app_context():
        exclusions = [row.fqdn for row in HostExclusion.query.order_by(HostExclusion.fqdn).all()]
        assert exclusions == ["host01.example.com", "host02.example.com"]


def test_invalid_host_exclusion_submit_preserves_text_and_rejects_invalid_entries(client, app):
    login(client, "admin")
    raw_text = "host01.example.com\nnot a fqdn\nhost02.example.com"
    response = client.post(
        "/hosts/exclusions",
        data={"host_exclusions": raw_text},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid FQDN value: not a fqdn" in response.data
    assert raw_text.encode() in response.data
    with app.app_context():
        assert HostExclusion.query.count() == 0


def test_re_saving_host_exclusions_replaces_previous_list(client, app):
    login(client, "admin")
    response = client.post(
        "/hosts/exclusions",
        data={"host_exclusions": "host01.example.com\nhost02.example.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    response = client.post(
        "/hosts/exclusions",
        data={"host_exclusions": "host03.example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        exclusions = [row.fqdn for row in HostExclusion.query.order_by(HostExclusion.fqdn).all()]
        assert exclusions == ["host03.example.com"]


def test_forekat_test_page_shows_loading_message_and_continue_button(client):
    login(client, "admin")

    response = client.get("/forekat/test")

    assert response.status_code == 200
    assert b"Retrieving data from ForeKat..." in response.data
    assert b"Continue to ForeKat Test" not in response.data
    assert b'data-loading-action-form' in response.data
    assert b'name="csrf_token"' in response.data
    assert b'loading-spinner' in response.data


def test_forekat_test_post_shows_connectivity_status(client, monkeypatch):
    login(client, "admin")

    def fake_snapshot(_client):
        return {
            "all_hosts": [{"id": 1, "fqdn": "host01.example.com"}],
            "warnings": [],
        }

    monkeypatch.setattr("app.main.get_inventory_snapshot", fake_snapshot)

    response = client.post("/forekat/test")

    assert response.status_code == 200
    assert b"API connectivity test completed." in response.data
    assert b"Foreman hosts: 1" in response.data
    assert b"Katello host collections" not in response.data


def test_assignment_page_has_single_collapsed_prefix_section(client, monkeypatch):
    login(client, "admin")

    def fake_snapshot(_client):
        return {
            "all_hosts": [
                {"id": 1, "fqdn": "kafka01-stage-bry.platform.is"},
                {"id": 2, "fqdn": "kafka02-stage-bry.platform.is"},
                {"id": 3, "fqdn": "kafka03-stage-bry.platform.is"},
            ],
            "warnings": [],
        }

    monkeypatch.setattr("app.services.assignment_persistence.get_inventory_snapshot", fake_snapshot)
    response = client.post("/assignments/generate", follow_redirects=False)
    assert response.status_code == 302

    response = client.get("/assignments/1")
    assert response.status_code == 200
    assert b"Host pool" in response.data
    assert response.data.count(b"Prefix Sequence Groups") == 1
    assert b"<details class=\"prefix-sequence-details\">" in response.data
    assert b"Pets" in response.data
    assert b"Assigned hosts" in response.data
    assert b"/assignments/generate/non-production" in response.data
    assert b"/assignments/generate/production" in response.data
    assert b"method=\"post\" action=\"/assignments/generate/non-production\"" not in response.data


def test_assignment_page_shows_selected_pool_name(client, app):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(
            host_count=3,
            user_count=2,
            pool_name="production",
            pool_collection_name="Production",
            excluded_host_count=5,
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    response = client.get(f"/assignments/{run_id}")

    assert response.status_code == 200
    assert b"Production" in response.data
    assert b"Production Pets" in response.data
    assert b"Excluded hosts: 5" in response.data


def test_assignment_page_shows_export_controls_for_admin(client, app):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(host_count=1, user_count=2, pool_name="production", pool_collection_name="Production")
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    response = client.get(f"/assignments/{run_id}")

    assert response.status_code == 200
    assert b"Change Request Number" in response.data
    assert b"Export as .xlsx and Download" in response.data
    assert b">Export</button>" not in response.data
    assert b"data-export-form" in response.data
    assert b'name="change_request_number"' in response.data
    assert f"/assignments/{run_id}/export".encode() in response.data


def test_assignment_export_requires_change_request_number(client, app):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(host_count=1, user_count=2, pool_name="production", pool_collection_name="Production")
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    response = client.post(
        f"/assignments/{run_id}/export",
        data={"change_request_number": "   "},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Change Request Number is required." in response.data


def test_assignment_export_route_returns_zip_download(client, app, monkeypatch, tmp_path):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(host_count=1, user_count=2, pool_name="production", pool_collection_name="Production")
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    def fake_export(run_id, change_request_number, output_dir, template_path=None):
        today = date.today().isoformat()
        zip_path = tmp_path / f"assignment_run_{run_id}_crq-1_{today}.zip"
        zip_path.write_bytes(b"zip-bytes")
        return ExportZipResult(
            zip_path=zip_path,
            zip_filename=zip_path.name,
            files=[],
            skipped_users=[],
            sheet_target=SimpleNamespace(title="Production-", path="xl/worksheets/sheet1.xml", hostname_column="B"),
        )

    monkeypatch.setattr("app.main.export_assignment_run_to_zip", fake_export)

    response = client.post(
        f"/assignments/{run_id}/export",
        data={"change_request_number": "CRQ 1"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert response.headers["Content-Disposition"].startswith("attachment;")
    assert f"assignment_run_{run_id}_crq-1_{date.today().isoformat()}.zip" in response.headers["Content-Disposition"]


def test_assignment_page_shows_non_production_pet_label(client, app):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(
            host_count=3,
            user_count=2,
            pool_name="non_production",
            pool_collection_name="Non-Production",
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    response = client.get(f"/assignments/{run_id}")

    assert response.status_code == 200
    assert b"Non-Production Pets" in response.data


def test_assignment_page_shows_only_pool_specific_pet_content(client, app):
    login(client, "admin")
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.assign_only_production_pets = True
        admin_user.assign_only_non_production_pets = False
        admin_user.pets.append(PetHost(fqdn="prod01.example.com", pet_type="production"))
        admin_user.pets.append(PetHost(fqdn="stage01.example.com", pet_type="non_production"))

        production_run = AssignmentRun(
            host_count=1,
            user_count=2,
            pool_name="production",
            pool_collection_name="Production",
        )
        non_production_run = AssignmentRun(
            host_count=1,
            user_count=2,
            pool_name="non_production",
            pool_collection_name="Non-Production",
        )
        db.session.add_all([production_run, non_production_run])
        db.session.commit()
        production_run_id = production_run.id
        non_production_run_id = non_production_run.id
        db.session.remove()

    production_response = client.get(f"/assignments/{production_run_id}")
    non_production_response = client.get(f"/assignments/{non_production_run_id}")

    assert b"prod01.example.com" in production_response.data
    assert b"stage01.example.com" not in production_response.data
    assert b"stage01.example.com" in non_production_response.data
    assert b"prod01.example.com" not in non_production_response.data


def test_assignment_detail_marks_user_for_selected_pool(app):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.assign_only_production_pets = True
        admin_user.assign_only_non_production_pets = False
        production_run = AssignmentRun(
            host_count=1,
            user_count=2,
            pool_name="production",
            pool_collection_name="Production",
        )
        non_production_run = AssignmentRun(
            host_count=1,
            user_count=2,
            pool_name="non_production",
            pool_collection_name="Non-Production",
        )
        db.session.add_all([production_run, non_production_run])
        db.session.commit()

        production_detail = _build_assignment_detail(production_run)
        non_production_detail = _build_assignment_detail(non_production_run)

        production_admin_row = next(
            row for row in production_detail["assignment_rows"] if row["user"].login_name == "admin"
        )
        non_production_admin_row = next(
            row for row in non_production_detail["assignment_rows"] if row["user"].login_name == "admin"
        )

        assert production_admin_row["assign_only_label"] == "Assign ONLY Production Pets"
        assert non_production_admin_row["assign_only_label"] is None


def test_assignment_page_shows_special_jboss_prefix_group(client, app):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(host_count=6, user_count=2, pool_name="production", pool_collection_name="Production")
        db.session.add(run)
        db.session.flush()
        db.session.add_all(
            [
                HostAssignment(
                    assignment_run_id=run.id,
                    user_id=1,
                    fqdn=f"jboss0{index}-prod-bry.platform.is",
                    source_type="prefix_sequence",
                    source_name="jboss-production-special",
                )
                for index in (1, 3, 5)
            ]
        )
        db.session.commit()
        run_id = run.id

    response = client.get(f"/assignments/{run_id}")

    assert response.status_code == 200
    assert response.data.count(b"Prefix Sequence Groups") == 1
    assert b"jboss-production-special" in response.data


def test_assignment_page_renders_source_dots_and_key(client, app):
    login(client, "admin")
    with app.app_context():
        run = AssignmentRun(host_count=4, user_count=2, pool_name="production", pool_collection_name="Production")
        db.session.add(run)
        db.session.flush()
        db.session.add_all(
            [
                HostAssignment(
                    assignment_run_id=run.id,
                    user_id=1,
                    fqdn="random01.example.com",
                    source_type="random",
                    source_name=None,
                ),
                HostAssignment(
                    assignment_run_id=run.id,
                    user_id=1,
                    fqdn="prefix01.example.com",
                    source_type="prefix_sequence",
                    source_name="kafka-stage.example.com[01-03]",
                ),
                HostAssignment(
                    assignment_run_id=run.id,
                    user_id=2,
                    fqdn="pet01.example.com",
                    source_type="pet",
                    source_name=None,
                ),
                HostAssignment(
                    assignment_run_id=run.id,
                    user_id=2,
                    fqdn="legacy01.example.com",
                    source_type="legacy_source",
                    source_name="legacy-group",
                ),
            ]
        )
        db.session.commit()
        run_id = run.id

    response = client.get(f"/assignments/{run_id}")

    assert response.status_code == 200
    assert b"KEY:" in response.data
    assert b"Random" in response.data
    assert b"Prefix Sequence" in response.data
    assert b"Pet" in response.data
    assert b"source-dot-random" in response.data
    assert b"source-dot-prefix-sequence" in response.data
    assert b"source-dot-pet" in response.data
    assert b"source-dot-unknown" in response.data
    assert b"random01.example.com" in response.data
    assert b"prefix01.example.com" in response.data
    assert b"pet01.example.com" in response.data
    assert b"legacy01.example.com" in response.data


def test_dashboard_shows_available_hosts_button_once(client):
    login(client, "admin")
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert response.data.count(b"Display All Available Hosts") == 1
    assert b"Generate Non-Production Hosts Assignment" in response.data
    assert b"Generate Production Hosts Assignment" in response.data
    assert b"Generate Balanced Assignment" not in response.data
    assert b"/assignments/generate/non-production" in response.data
    assert b"/assignments/generate/production" in response.data
    assert b"method=\"post\" action=\"/assignments/generate/non-production\"" not in response.data


def test_dashboard_hosts_management_section_includes_host_exclusions_link(client):
    login(client, "admin")
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Hosts Management" in response.data
    assert b"Functions for ForeKat host processing" in response.data
    assert b"Host Exclusions List" in response.data
    assert b"Documentation" in response.data
    assert b"<h3><i data-lucide=\"server\"></i> Available Hosts</h3>" not in response.data


def test_documentation_page_explains_assignment_rules(client):
    login(client, "admin")

    response = client.get("/documentation")

    assert response.status_code == 200
    assert b"Documentation" in response.data
    assert b"Host Pools" in response.data
    assert b"Host Exclusions" in response.data
    assert b"Pets First" in response.data
    assert b"Prefix Sequence Grouping" in response.data
    assert b"Special JBoss Groups" in response.data
    assert b"Assign ONLY Pets" in response.data
    assert b"least-loaded eligible user" in response.data
    assert b"total assigned host count" in response.data


def test_dashboard_shows_schema_warning_when_assignment_run_columns_missing(client, monkeypatch):
    login(client, "admin")
    monkeypatch.setattr("app.main._assignment_run_schema_ready", lambda: False)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"database schema is upgraded" in response.data


def test_user_form_contains_interactive_pet_controls(client):
    login(client, "admin")
    response = client.get("/users/new")

    assert response.status_code == 200
    assert b'data-user-pet-form' in response.data
    assert response.data.count(b'data-pet-widget') == 2
    assert response.data.count(b'data-pet-input') == 2
    assert response.data.count(b'data-pet-add') == 2
    assert response.data.count(b'data-pet-list') == 2
    assert response.data.count(b'data-pet-remove') == 2
    assert response.data.count(b'<textarea') >= 2
    assert response.data.count(b'name="production_pet_blob"') == 1
    assert response.data.count(b'name="non_production_pet_blob"') == 1
    assert b"Production Pets" in response.data
    assert b"Non-Production Pets" in response.data
    assert b"Assign ONLY Production Pets" in response.data
    assert b"Assign ONLY Non-Production Pets" in response.data


def test_pets_page_shows_both_pet_categories(client, app):
    login(client, "admin")
    response = client.get("/pets")

    assert response.status_code == 200
    assert b"Production Pets" in response.data
    assert b"Non-Production Pets" in response.data


def test_csrf_is_active_when_enabled(tmp_path: Path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}",
            "WTF_CSRF_ENABLED": True,
        }
    )
    with app.test_client() as client:
        response = client.post("/login", data={"login_name": "admin", "password": "password123"})
        assert response.status_code == 400
