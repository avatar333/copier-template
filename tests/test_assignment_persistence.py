from __future__ import annotations

from app.extensions import db
from app.models import (
    AppUser,
    AssignmentRun,
    HostAssignment,
    HostExclusion,
    PET_TYPE_NON_PRODUCTION,
    PET_TYPE_PRODUCTION,
    PetHost,
)
from app.services import assignment_persistence


def test_generate_and_persist_assignment_creates_run(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.pets.append(PetHost(fqdn="pet01.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        db.session.commit()

        def fake_snapshot(_client):
            return {
                "all_hosts": [
                    {"id": 1, "fqdn": "pet01.example.com"},
                    {"id": 2, "fqdn": "db01.example.com"},
                    {"id": 3, "fqdn": "db02.example.com"},
                    {"id": 4, "fqdn": "web01.example.com"},
                ],
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_inventory_snapshot", fake_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(admin_user.id, client=object())

        assert run.host_count == 4
        assert run.user_count == 2
        assert db.session.query(AssignmentRun).count() == 1
        assert db.session.query(HostAssignment).count() == 4


def test_production_assignment_uses_only_production_pets(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.pets.append(PetHost(fqdn="prod01.example.com", pet_type=PET_TYPE_PRODUCTION))
        admin_user.pets.append(PetHost(fqdn="prod02.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "prod01.example.com"},
                    {"id": 2, "fqdn": "prod02.example.com"},
                    {"id": 3, "fqdn": "prod03.example.com"},
                ],
                "all_hosts": [
                    {"id": 1, "fqdn": "prod01.example.com"},
                    {"id": 2, "fqdn": "prod02.example.com"},
                    {"id": 3, "fqdn": "prod03.example.com"},
                ],
                "available_hosts": [
                    {"id": 1, "fqdn": "prod01.example.com"},
                    {"id": 2, "fqdn": "prod02.example.com"},
                    {"id": 3, "fqdn": "prod03.example.com"},
                ],
                "pool_name": "production",
                "collection_name": "Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="production",
            client=object(),
        )

        assignments = {assignment.fqdn: assignment.source_type for assignment in run.assignments}
        assert assignments["prod01.example.com"] == "pet"
        assert assignments["prod02.example.com"] != "pet"


def test_non_production_assignment_uses_only_non_production_pets_and_warns_on_out_of_pool_pets(
    app, monkeypatch
):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        regular_user = AppUser.query.filter_by(login_name="regular").first()
        admin_user.pets.append(PetHost(fqdn="prod01.example.com", pet_type=PET_TYPE_PRODUCTION))
        admin_user.pets.append(PetHost(fqdn="stage01.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        regular_user.pets.append(PetHost(fqdn="stage02.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "non_production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "prod01.example.com"},
                    {"id": 2, "fqdn": "stage01.example.com"},
                    {"id": 3, "fqdn": "stage02.example.com"},
                    {"id": 4, "fqdn": "stage03.example.com"},
                ],
                "all_hosts": [
                    {"id": 2, "fqdn": "stage01.example.com"},
                    {"id": 3, "fqdn": "stage02.example.com"},
                    {"id": 4, "fqdn": "stage03.example.com"},
                ],
                "available_hosts": [
                    {"id": 2, "fqdn": "stage01.example.com"},
                    {"id": 3, "fqdn": "stage02.example.com"},
                    {"id": 4, "fqdn": "stage03.example.com"},
                ],
                "pool_name": "non_production",
                "collection_name": "Non-Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="non_production",
            client=object(),
        )

        warnings = [warning.message for warning in run.warnings]
        assignments = {assignment.fqdn: assignment.source_type for assignment in run.assignments}
        assert assignments["stage01.example.com"] == "pet"
        assert assignments["stage02.example.com"] == "pet"
        assert "prod01.example.com" not in assignments
        assert all("Production pet host prod01.example.com" not in warning for warning in warnings)


def test_production_assignment_warns_for_selected_pet_type_outside_selected_pool(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.pets.append(PetHost(fqdn="prod01.example.com", pet_type=PET_TYPE_PRODUCTION))
        admin_user.pets.append(PetHost(fqdn="prod02.example.com", pet_type=PET_TYPE_PRODUCTION))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "prod01.example.com"},
                    {"id": 2, "fqdn": "prod02.example.com"},
                    {"id": 3, "fqdn": "prod03.example.com"},
                ],
                "all_hosts": [
                    {"id": 2, "fqdn": "prod02.example.com"},
                    {"id": 3, "fqdn": "prod03.example.com"},
                ],
                "available_hosts": [
                    {"id": 2, "fqdn": "prod02.example.com"},
                    {"id": 3, "fqdn": "prod03.example.com"},
                ],
                "pool_name": "production",
                "collection_name": "Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="production",
            client=object(),
        )

        warnings = [warning.message for warning in run.warnings]
        assignments = {assignment.fqdn: assignment.source_type for assignment in run.assignments}
        assert assignments["prod02.example.com"] == "pet"
        assert "prod01.example.com" not in assignments
        assert any(
            "Production pet host prod01.example.com" in warning
            and "selected Production pool" in warning
            for warning in warnings
        )


def test_assign_only_selected_pool_pets_user_receives_only_selected_pool_pet_type(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        regular_user = AppUser.query.filter_by(login_name="regular").first()
        admin_user.assign_only_non_production_pets = True
        admin_user.assign_only_pets = True
        admin_user.pets.append(PetHost(fqdn="stage01.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        admin_user.pets.append(PetHost(fqdn="prod01.example.com", pet_type=PET_TYPE_PRODUCTION))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "non_production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "stage01.example.com"},
                    {"id": 2, "fqdn": "prod01.example.com"},
                    {"id": 3, "fqdn": "stage02.example.com"},
                    {"id": 4, "fqdn": "stage03.example.com"},
                ],
                "all_hosts": [
                    {"id": 1, "fqdn": "stage01.example.com"},
                    {"id": 3, "fqdn": "stage02.example.com"},
                    {"id": 4, "fqdn": "stage03.example.com"},
                ],
                "available_hosts": [
                    {"id": 1, "fqdn": "stage01.example.com"},
                    {"id": 3, "fqdn": "stage02.example.com"},
                    {"id": 4, "fqdn": "stage03.example.com"},
                ],
                "pool_name": "non_production",
                "collection_name": "Non-Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            regular_user.id,
            pool_name="non_production",
            client=object(),
        )

        assignments_by_user = {}
        for assignment in run.assignments:
            assignments_by_user.setdefault(assignment.user_id, []).append(assignment)

        admin_assignments = assignments_by_user[admin_user.id]
        assert [(assignment.fqdn, assignment.source_type) for assignment in admin_assignments] == [
            ("stage01.example.com", "pet")
        ]
        assert all(assignment.fqdn != "prod01.example.com" for assignment in run.assignments)


def test_production_assignment_filters_excluded_hosts_before_assignment(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.pets.append(PetHost(fqdn="pet01.example.com", pet_type=PET_TYPE_PRODUCTION))
        db.session.add(HostExclusion(fqdn="db02.example.com"))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "pet01.example.com"},
                    {"id": 2, "fqdn": "kafka01-stage-bry.platform.is"},
                    {"id": 3, "fqdn": "kafka02-stage-bry.platform.is"},
                    {"id": 4, "fqdn": "kafka03-stage-bry.platform.is"},
                    {"id": 5, "fqdn": "db01.example.com"},
                    {"id": 6, "fqdn": "db02.example.com"},
                ],
                "all_hosts": [
                    {"id": 1, "fqdn": "pet01.example.com"},
                    {"id": 2, "fqdn": "kafka01-stage-bry.platform.is"},
                    {"id": 3, "fqdn": "kafka02-stage-bry.platform.is"},
                    {"id": 4, "fqdn": "kafka03-stage-bry.platform.is"},
                    {"id": 5, "fqdn": "db01.example.com"},
                    {"id": 6, "fqdn": "db02.example.com"},
                ],
                "available_hosts": [
                    {"id": 1, "fqdn": "pet01.example.com"},
                    {"id": 2, "fqdn": "kafka01-stage-bry.platform.is"},
                    {"id": 3, "fqdn": "kafka02-stage-bry.platform.is"},
                    {"id": 4, "fqdn": "kafka03-stage-bry.platform.is"},
                    {"id": 5, "fqdn": "db01.example.com"},
                    {"id": 6, "fqdn": "db02.example.com"},
                ],
                "pool_name": "production",
                "collection_name": "Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="production",
            client=object(),
        )

        assigned_fqdns = {assignment.fqdn for assignment in run.assignments}
        warnings = [warning.message for warning in run.warnings]
        assert run.excluded_host_count == 1
        assert "db02.example.com" not in assigned_fqdns
        assert any("Excluded hosts removed from the selected Production pool" in warning for warning in warnings)


def test_non_production_assignment_filters_excluded_hosts_before_assignment(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.pets.append(PetHost(fqdn="stage01.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        db.session.add(HostExclusion(fqdn="stage02.example.com"))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "non_production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "stage01.example.com"},
                    {"id": 2, "fqdn": "stage02.example.com"},
                    {"id": 3, "fqdn": "web01.example.com"},
                    {"id": 4, "fqdn": "web02.example.com"},
                ],
                "all_hosts": [
                    {"id": 1, "fqdn": "stage01.example.com"},
                    {"id": 2, "fqdn": "stage02.example.com"},
                    {"id": 3, "fqdn": "web01.example.com"},
                    {"id": 4, "fqdn": "web02.example.com"},
                ],
                "available_hosts": [
                    {"id": 1, "fqdn": "stage01.example.com"},
                    {"id": 2, "fqdn": "stage02.example.com"},
                    {"id": 3, "fqdn": "web01.example.com"},
                    {"id": 4, "fqdn": "web02.example.com"},
                ],
                "pool_name": "non_production",
                "collection_name": "Non-Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="non_production",
            client=object(),
        )

        assigned_fqdns = {assignment.fqdn for assignment in run.assignments}
        warnings = [warning.message for warning in run.warnings]
        assert run.excluded_host_count == 1
        assert "stage02.example.com" not in assigned_fqdns
        assert any("Excluded hosts removed from the selected Non-Production pool" in warning for warning in warnings)


def test_excluded_pet_hosts_are_not_assigned_and_warn(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        admin_user.pets.append(PetHost(fqdn="jboss01-prod-bry.platform.is", pet_type=PET_TYPE_PRODUCTION))
        db.session.add(HostExclusion(fqdn="jboss01-prod-bry.platform.is"))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "jboss01-prod-bry.platform.is"},
                    {"id": 2, "fqdn": "db01.example.com"},
                ],
                "all_hosts": [
                    {"id": 1, "fqdn": "jboss01-prod-bry.platform.is"},
                    {"id": 2, "fqdn": "db01.example.com"},
                ],
                "available_hosts": [
                    {"id": 1, "fqdn": "jboss01-prod-bry.platform.is"},
                    {"id": 2, "fqdn": "db01.example.com"},
                ],
                "pool_name": "production",
                "collection_name": "Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="production",
            client=object(),
        )

        assigned_fqdns = {assignment.fqdn for assignment in run.assignments}
        warnings = [warning.message for warning in run.warnings]
        assert "jboss01-prod-bry.platform.is" not in assigned_fqdns
        assert any(
            "Pet host jboss01-prod-bry.platform.is for Admin User is excluded" in warning
            for warning in warnings
        )


def test_excluded_special_jboss_hosts_are_not_assigned(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        db.session.add(HostExclusion(fqdn="jboss02-prod-pkl.platform.is"))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "production"
            return {
                "all_foreman_hosts": [
                    {"id": index, "fqdn": host}
                    for index, host in enumerate(
                        [
                            "jboss01-prod-bry.platform.is",
                            "jboss02-prod-pkl.platform.is",
                            "jboss03-prod-bry.platform.is",
                            "jboss04-prod-pkl.platform.is",
                            "jboss05-prod-bry.platform.is",
                            "jboss06-prod-pkl.platform.is",
                            "db01.example.com",
                        ],
                        start=1,
                    )
                ],
                "all_hosts": [
                    {"id": index, "fqdn": host}
                    for index, host in enumerate(
                        [
                            "jboss01-prod-bry.platform.is",
                            "jboss02-prod-pkl.platform.is",
                            "jboss03-prod-bry.platform.is",
                            "jboss04-prod-pkl.platform.is",
                            "jboss05-prod-bry.platform.is",
                            "jboss06-prod-pkl.platform.is",
                            "db01.example.com",
                        ],
                        start=1,
                    )
                ],
                "available_hosts": [
                    {"id": index, "fqdn": host}
                    for index, host in enumerate(
                        [
                            "jboss01-prod-bry.platform.is",
                            "jboss02-prod-pkl.platform.is",
                            "jboss03-prod-bry.platform.is",
                            "jboss04-prod-pkl.platform.is",
                            "jboss05-prod-bry.platform.is",
                            "jboss06-prod-pkl.platform.is",
                            "db01.example.com",
                        ],
                        start=1,
                    )
                ],
                "pool_name": "production",
                "collection_name": "Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="production",
            client=object(),
        )

        assigned_fqdns = {assignment.fqdn for assignment in run.assignments}
        warnings = [warning.message for warning in run.warnings]
        assert "jboss02-prod-pkl.platform.is" not in assigned_fqdns
        assert any("Special JBoss host jboss02-prod-pkl.platform.is is excluded" in warning for warning in warnings)
        assert any(
            assignment.source_type == "prefix_sequence" and assignment.source_name == "jboss-production-special"
            for assignment in run.assignments
        )


def test_prefix_sequence_and_random_assignment_ignore_excluded_hosts(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        regular_user = AppUser.query.filter_by(login_name="regular").first()
        db.session.add(HostExclusion(fqdn="kafka03-stage-bry.platform.is"))
        db.session.add(HostExclusion(fqdn="web02.example.com"))
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "kafka01-stage-bry.platform.is"},
                    {"id": 2, "fqdn": "kafka02-stage-bry.platform.is"},
                    {"id": 3, "fqdn": "kafka03-stage-bry.platform.is"},
                    {"id": 4, "fqdn": "web01.example.com"},
                    {"id": 5, "fqdn": "web02.example.com"},
                ],
                "all_hosts": [
                    {"id": 1, "fqdn": "kafka01-stage-bry.platform.is"},
                    {"id": 2, "fqdn": "kafka02-stage-bry.platform.is"},
                    {"id": 3, "fqdn": "kafka03-stage-bry.platform.is"},
                    {"id": 4, "fqdn": "web01.example.com"},
                    {"id": 5, "fqdn": "web02.example.com"},
                ],
                "available_hosts": [
                    {"id": 1, "fqdn": "kafka01-stage-bry.platform.is"},
                    {"id": 2, "fqdn": "kafka02-stage-bry.platform.is"},
                    {"id": 3, "fqdn": "kafka03-stage-bry.platform.is"},
                    {"id": 4, "fqdn": "web01.example.com"},
                    {"id": 5, "fqdn": "web02.example.com"},
                ],
                "pool_name": "production",
                "collection_name": "Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="production",
            client=object(),
        )

        assigned_fqdns = {assignment.fqdn for assignment in run.assignments}
        assert "kafka03-stage-bry.platform.is" not in assigned_fqdns
        assert "web02.example.com" not in assigned_fqdns
        assert any(assignment.source_type == "prefix_sequence" for assignment in run.assignments)
        assert any(assignment.source_type == "random" for assignment in run.assignments)
        assert run.excluded_host_count == 2


def test_all_selected_pool_hosts_excluded_creates_empty_run_with_warning(app, monkeypatch):
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        db.session.add_all(
            [
                HostExclusion(fqdn="db01.example.com"),
                HostExclusion(fqdn="db02.example.com"),
            ]
        )
        db.session.commit()

        def fake_pool_snapshot(_client, pool_name):
            assert pool_name == "production"
            return {
                "all_foreman_hosts": [
                    {"id": 1, "fqdn": "db01.example.com"},
                    {"id": 2, "fqdn": "db02.example.com"},
                ],
                "all_hosts": [
                    {"id": 1, "fqdn": "db01.example.com"},
                    {"id": 2, "fqdn": "db02.example.com"},
                ],
                "available_hosts": [
                    {"id": 1, "fqdn": "db01.example.com"},
                    {"id": 2, "fqdn": "db02.example.com"},
                ],
                "pool_name": "production",
                "collection_name": "Production",
                "warnings": [],
            }

        monkeypatch.setattr(assignment_persistence, "get_hosts_for_assignment_pool", fake_pool_snapshot)

        run = assignment_persistence.generate_and_persist_assignment(
            admin_user.id,
            pool_name="production",
            client=object(),
        )

        warnings = [warning.message for warning in run.warnings]
        assert run.host_count == 0
        assert run.excluded_host_count == 2
        assert run.assignments == []
        assert any("All hosts in the selected Production pool are excluded." in warning for warning in warnings)
