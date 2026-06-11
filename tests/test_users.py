from __future__ import annotations

from conftest import login
from app.extensions import db
from app.models import (
    AppUser,
    AssignmentRun,
    HostAssignment,
    PET_TYPE_NON_PRODUCTION,
    PET_TYPE_PRODUCTION,
    PetHost,
)


def pet_blob(*pets: str) -> str:
    return "\n".join(pets)


def user_form_data(
    *,
    login_name: str,
    first_name: str,
    last_name: str,
    password: str = "",
    is_active: str = "y",
    is_admin: str = "",
    assign_only_production_pets: str = "",
    assign_only_non_production_pets: str = "",
    production_pets: tuple[str, ...] = (),
    non_production_pets: tuple[str, ...] = (),
) -> dict[str, str]:
    return {
        "login_name": login_name,
        "first_name": first_name,
        "last_name": last_name,
        "password": password,
        "is_active": is_active,
        "is_admin": is_admin,
        "assign_only_production_pets": assign_only_production_pets,
        "assign_only_non_production_pets": assign_only_non_production_pets,
        "production_pet_blob": pet_blob(*production_pets),
        "non_production_pet_blob": pet_blob(*non_production_pets),
    }


def pets_by_type(user: AppUser) -> dict[str, list[str]]:
    return {
        PET_TYPE_PRODUCTION: [pet.fqdn for pet in user.pets if pet.pet_type == PET_TYPE_PRODUCTION],
        PET_TYPE_NON_PRODUCTION: [
            pet.fqdn for pet in user.pets if pet.pet_type == PET_TYPE_NON_PRODUCTION
        ],
    }


def test_regular_user_cannot_access_user_list(client):
    login(client, "regular")
    response = client.get("/users/")
    assert response.status_code == 403


def test_regular_user_cannot_create_users(client):
    login(client, "regular")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="newuser",
            first_name="New",
            last_name="User",
            password="password123",
        ),
    )
    assert response.status_code == 403


def test_admin_can_create_user_with_production_pets(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="newuser",
            first_name="New",
            last_name="User",
            password="password123",
            production_pets=("HOST01.EXAMPLE.COM", "host02.example.com"),
        ),
        follow_redirects=True,
    )
    assert b"User created." in response.data
    with app.app_context():
        created = AppUser.query.filter_by(login_name="newuser").first()
        assert created is not None
        assert created.assign_only_pets is False
        assert created.assign_only_production_pets is False
        assert created.assign_only_non_production_pets is False
        assert pets_by_type(created) == {
            PET_TYPE_PRODUCTION: ["host01.example.com", "host02.example.com"],
            PET_TYPE_NON_PRODUCTION: [],
        }


def test_admin_can_create_user_with_non_production_pets(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="stageuser",
            first_name="Stage",
            last_name="User",
            password="password123",
            non_production_pets=("host03.example.com",),
        ),
        follow_redirects=True,
    )
    assert b"User created." in response.data
    with app.app_context():
        created = AppUser.query.filter_by(login_name="stageuser").first()
        assert created is not None
        assert pets_by_type(created) == {
            PET_TYPE_PRODUCTION: [],
            PET_TYPE_NON_PRODUCTION: ["host03.example.com"],
        }


def test_admin_can_create_user_with_assign_only_production_pets(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="petsonly",
            first_name="Pets",
            last_name="Only",
            password="password123",
            assign_only_production_pets="y",
            production_pets=("host01.example.com",),
        ),
        follow_redirects=True,
    )
    assert b"User created." in response.data
    with app.app_context():
        created = AppUser.query.filter_by(login_name="petsonly").first()
        assert created is not None
        assert created.assign_only_pets is True
        assert created.assign_only_production_pets is True
        assert created.assign_only_non_production_pets is False


def test_admin_can_create_user_with_assign_only_non_production_pets(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="stagepetsonly",
            first_name="Stage",
            last_name="Only",
            password="password123",
            assign_only_non_production_pets="y",
            non_production_pets=("host03.example.com",),
        ),
        follow_redirects=True,
    )
    assert b"User created." in response.data
    with app.app_context():
        created = AppUser.query.filter_by(login_name="stagepetsonly").first()
        assert created is not None
        assert created.assign_only_pets is True
        assert created.assign_only_production_pets is False
        assert created.assign_only_non_production_pets is True


def test_duplicate_production_pets_in_same_form_are_rejected(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="dupuser",
            first_name="Dup",
            last_name="User",
            password="password123",
            production_pets=("host01.example.com", "HOST01.EXAMPLE.COM"),
        ),
        follow_redirects=True,
    )
    assert b"Duplicate pet FQDNs are not allowed" in response.data
    with app.app_context():
        assert AppUser.query.filter_by(login_name="dupuser").first() is None


def test_duplicate_non_production_pets_in_same_form_are_rejected(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="dupstage",
            first_name="Dup",
            last_name="Stage",
            password="password123",
            non_production_pets=("host01.example.com", "HOST01.EXAMPLE.COM"),
        ),
        follow_redirects=True,
    )
    assert b"Duplicate pet FQDNs are not allowed" in response.data
    with app.app_context():
        assert AppUser.query.filter_by(login_name="dupstage").first() is None


def test_invalid_pet_fqdn_is_rejected(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="badpetuser",
            first_name="Bad",
            last_name="Pet",
            password="password123",
            production_pets=("not a fqdn",),
        ),
        follow_redirects=True,
    )
    assert b"Invalid FQDN value" in response.data
    with app.app_context():
        assert AppUser.query.filter_by(login_name="badpetuser").first() is None


def test_failed_validation_preserves_both_submitted_pet_lists(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            production_pets=("prod05.example.com",),
            non_production_pets=("not a fqdn", "stage05.example.com"),
        ),
        follow_redirects=True,
    )
    assert b"Invalid FQDN value" in response.data
    assert b"prod05.example.com" in response.data
    assert b"stage05.example.com" in response.data


def test_edit_user_adds_and_removes_production_pets(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular.pets.append(PetHost(fqdn="prod01.example.com", pet_type=PET_TYPE_PRODUCTION))
        db.session.commit()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            production_pets=("prod02.example.com",),
        ),
        follow_redirects=True,
    )
    assert b"User updated." in response.data
    with app.app_context():
        regular = db.session.get(AppUser, regular_id)
        assert pets_by_type(regular) == {
            PET_TYPE_PRODUCTION: ["prod02.example.com"],
            PET_TYPE_NON_PRODUCTION: [],
        }
        assert (
            PetHost.query.filter_by(fqdn="prod01.example.com", pet_type=PET_TYPE_PRODUCTION).first()
            is None
        )


def test_edit_user_adds_and_removes_non_production_pets(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular.pets.append(PetHost(fqdn="stage01.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        db.session.commit()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            non_production_pets=("stage02.example.com",),
        ),
        follow_redirects=True,
    )
    assert b"User updated." in response.data
    with app.app_context():
        regular = db.session.get(AppUser, regular_id)
        assert pets_by_type(regular) == {
            PET_TYPE_PRODUCTION: [],
            PET_TYPE_NON_PRODUCTION: ["stage02.example.com"],
        }
        assert (
            PetHost.query.filter_by(fqdn="stage01.example.com", pet_type=PET_TYPE_NON_PRODUCTION).first()
            is None
        )


def test_same_fqdn_cannot_be_assigned_to_two_users_for_same_pet_type(client, app):
    login(client, "admin")
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        regular = AppUser.query.filter_by(login_name="regular").first()
        admin_user.pets.append(PetHost(fqdn="shared.example.com", pet_type=PET_TYPE_PRODUCTION))
        db.session.commit()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            production_pets=("shared.example.com",),
        ),
        follow_redirects=True,
    )
    assert b"Production pet shared.example.com is already assigned to Admin User." in response.data


def test_same_fqdn_may_be_assigned_once_per_pet_type(client, app):
    login(client, "admin")
    with app.app_context():
        admin_user = AppUser.query.filter_by(login_name="admin").first()
        regular = AppUser.query.filter_by(login_name="regular").first()
        admin_user.pets.append(PetHost(fqdn="shared.example.com", pet_type=PET_TYPE_PRODUCTION))
        db.session.commit()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            non_production_pets=("shared.example.com",),
        ),
        follow_redirects=True,
    )
    assert b"User updated." in response.data
    with app.app_context():
        regular = db.session.get(AppUser, regular_id)
        assert pets_by_type(regular)[PET_TYPE_NON_PRODUCTION] == ["shared.example.com"]


def test_regular_user_can_edit_only_self(client, app):
    login(client, "regular")
    with app.app_context():
        admin = AppUser.query.filter_by(login_name="admin").first()
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular_id = regular.id
        admin_id = admin.id

    own_response = client.get(f"/users/{regular_id}/edit")
    other_response = client.get(f"/users/{admin_id}/edit")
    assert own_response.status_code == 200
    assert other_response.status_code == 403


def test_user_can_edit_own_password(client, app):
    login(client, "regular")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            password="newpassword123",
        ),
        follow_redirects=True,
    )
    assert b"User updated." in response.data
    with app.app_context():
        regular = db.session.get(AppUser, regular_id)
        assert regular.check_password("newpassword123")


def test_admin_cannot_demote_last_admin(client, app):
    login(client, "admin")
    with app.app_context():
        admin = AppUser.query.filter_by(login_name="admin").first()
        admin_id = admin.id

    response = client.post(
        f"/users/{admin_id}/edit",
        data=user_form_data(
            login_name="admin",
            first_name="Admin",
            last_name="User",
        ),
        follow_redirects=True,
    )
    assert b"Cannot demote the last admin user." in response.data


def test_admin_can_toggle_each_assign_only_flag_independently(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            assign_only_production_pets="y",
        ),
        follow_redirects=True,
    )
    assert b"User updated." in response.data
    with app.app_context():
        regular = db.session.get(AppUser, regular_id)
        assert regular.assign_only_production_pets is True
        assert regular.assign_only_non_production_pets is False
        assert regular.assign_only_pets is True


def test_regular_user_can_toggle_own_non_production_assign_only_flag(client, app):
    login(client, "regular")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            assign_only_non_production_pets="y",
        ),
        follow_redirects=True,
    )
    assert b"User updated." in response.data
    with app.app_context():
        regular = db.session.get(AppUser, regular_id)
        assert regular.assign_only_production_pets is False
        assert regular.assign_only_non_production_pets is True
        assert regular.assign_only_pets is True


def test_validation_failure_preserves_both_assign_only_checkbox_values(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular_id = regular.id

    response = client.post(
        f"/users/{regular_id}/edit",
        data=user_form_data(
            login_name="regular",
            first_name="Regular",
            last_name="User",
            assign_only_production_pets="y",
            assign_only_non_production_pets="y",
            production_pets=("not a fqdn",),
        ),
        follow_redirects=True,
    )

    assert b"Invalid FQDN value" in response.data
    assert b"Assign ONLY Production Pets" in response.data
    assert b"Assign ONLY Non-Production Pets" in response.data
    assert response.data.count(b'checked') >= 2


def test_users_list_displays_split_pet_counts_and_assign_only_flags(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular.assign_only_production_pets = True
        regular.pets.append(PetHost(fqdn="prod01.example.com", pet_type=PET_TYPE_PRODUCTION))
        regular.pets.append(PetHost(fqdn="stage01.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        db.session.commit()

    response = client.get("/users/")

    assert response.status_code == 200
    assert b"Production Pets" in response.data
    assert b"Non-Production Pets" in response.data
    assert b"Assign ONLY Production Pets" in response.data
    assert b"Assign ONLY Non-Production Pets" in response.data


def test_non_admin_cannot_delete_users(client, app):
    login(client, "regular")
    with app.app_context():
        admin = AppUser.query.filter_by(login_name="admin").first()
        admin_id = admin.id

    response = client.post(f"/users/{admin_id}/delete", follow_redirects=False)
    assert response.status_code == 403


def test_admin_can_delete_non_last_admin_user(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        regular_id = regular.id

    response = client.post(f"/users/{regular_id}/delete", follow_redirects=True)
    assert b"User deleted." in response.data
    with app.app_context():
        assert db.session.get(AppUser, regular_id) is None


def test_last_admin_cannot_be_deleted(client, app):
    login(client, "admin")
    with app.app_context():
        regular = AppUser.query.filter_by(login_name="regular").first()
        admin = AppUser.query.filter_by(login_name="admin").first()
        db.session.delete(regular)
        db.session.commit()
        admin_id = admin.id

    response = client.post(f"/users/{admin_id}/delete", follow_redirects=True)
    assert b"Cannot delete the last admin user." in response.data


def test_delete_user_with_pets_succeeds_and_cascades_pets(client, app):
    login(client, "admin")
    with app.app_context():
        temp = AppUser(
            login_name="tempuser",
            first_name="Temp",
            last_name="User",
            is_admin=False,
            is_active=True,
        )
        temp.set_password("password123")
        temp.pets.append(PetHost(fqdn="temp01.example.com", pet_type=PET_TYPE_PRODUCTION))
        temp.pets.append(PetHost(fqdn="temp02.example.com", pet_type=PET_TYPE_NON_PRODUCTION))
        db.session.add(temp)
        db.session.commit()
        temp_id = temp.id

    response = client.post(f"/users/{temp_id}/delete", follow_redirects=True)
    assert b"User deleted." in response.data
    with app.app_context():
        assert db.session.get(AppUser, temp_id) is None
        assert PetHost.query.filter_by(fqdn="temp01.example.com", pet_type=PET_TYPE_PRODUCTION).first() is None
        assert (
            PetHost.query.filter_by(fqdn="temp02.example.com", pet_type=PET_TYPE_NON_PRODUCTION).first()
            is None
        )


def test_delete_user_with_historical_assignment_rows_does_not_break_app(client, app):
    login(client, "admin")
    with app.app_context():
        temp = AppUser(
            login_name="historyuser",
            first_name="History",
            last_name="User",
            is_admin=False,
            is_active=True,
        )
        temp.set_password("password123")
        db.session.add(temp)
        db.session.flush()
        run = AssignmentRun(host_count=1, user_count=1)
        db.session.add(run)
        db.session.flush()
        assignment = HostAssignment(
            assignment_run_id=run.id,
            user_id=temp.id,
            fqdn="history01.example.com",
            source_type="random",
            source_name=None,
        )
        db.session.add(assignment)
        db.session.commit()
        temp_id = temp.id
        run_id = run.id
        assignment_id = assignment.id

    response = client.post(f"/users/{temp_id}/delete", follow_redirects=True)
    assert b"User deleted." in response.data
    with app.app_context():
        assignment = db.session.get(HostAssignment, assignment_id)
        assert assignment is not None
        assert assignment.user_id is None

    run_response = client.get(f"/assignments/{run_id}")
    assert run_response.status_code == 200


def test_admin_can_create_user_with_login_name(client, app):
    login(client, "admin")
    response = client.post(
        "/users/new",
        data=user_form_data(
            login_name="newuser",
            first_name="New",
            last_name="User",
            password="password123",
        ),
        follow_redirects=True,
    )
    assert b"User created." in response.data
    with app.app_context():
        created = AppUser.query.filter_by(login_name="newuser").first()
        assert created is not None
