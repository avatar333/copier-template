from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from .forms import UserForm
from .models import (
    AppUser,
    HostAssignment,
    PET_TYPE_NON_PRODUCTION,
    PET_TYPE_PRODUCTION,
    PetHost,
    pet_type_label,
)
from .services import parse_unique_fqdn_lines
from .extensions import db
from .permissions import require_admin, require_owner_or_admin


users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
@login_required
def list_users():
    require_admin()
    users = AppUser.query.order_by(AppUser.first_name, AppUser.last_name).all()
    return render_template("users.html", users=users)


@users_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_user():
    require_admin()

    form = UserForm()
    pet_items_by_type, pet_error_messages = _submitted_pet_items_by_type()
    is_valid = form.validate_on_submit()
    if request.method == "POST" and not form.password.data:
        form.password.errors.append("Password is required for new users.")
        is_valid = False

    if is_valid and not pet_error_messages:
        user = AppUser(
            login_name=form.login_name.data.strip().lower(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            is_admin=form.is_admin.data,
            assign_only_pets=(
                form.assign_only_production_pets.data or form.assign_only_non_production_pets.data
            ),
            assign_only_production_pets=form.assign_only_production_pets.data,
            assign_only_non_production_pets=form.assign_only_non_production_pets.data,
            is_active=form.is_active.data,
        )
        user.set_password(form.password.data)
        try:
            db.session.add(user)
            db.session.flush()
            _sync_user_pets(user, pet_items_by_type)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            pet_error_messages.append(str(exc))
        except IntegrityError:
            db.session.rollback()
            form.login_name.errors.append("That login name, person, or pet assignment already exists.")
        else:
            flash("User created.", "success")
            return redirect(url_for("users.list_users"))

    return _render_user_form(
        form,
        target_user=None,
        pet_items_by_type=pet_items_by_type,
        pet_errors=pet_error_messages,
    )


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(user_id: int):
    user = db.get_or_404(AppUser, user_id)
    require_owner_or_admin(user.id)

    form = UserForm(obj=user)
    pet_items_by_type = _current_pet_items_by_type(user)
    pet_error_messages: list[str] = []
    if request.method == "POST":
        pet_items_by_type, pet_error_messages = _submitted_pet_items_by_type()
    if not form.is_submitted():
        form.is_active.data = user.is_active

    if form.validate_on_submit() and not pet_error_messages:
        user.login_name = form.login_name.data.strip().lower()
        user.first_name = form.first_name.data.strip()
        user.last_name = form.last_name.data.strip()
        user.assign_only_production_pets = form.assign_only_production_pets.data
        user.assign_only_non_production_pets = form.assign_only_non_production_pets.data
        user.assign_only_pets = (
            user.assign_only_production_pets or user.assign_only_non_production_pets
        )
        if current_user.is_admin:
            if user.is_admin and not form.is_admin.data and _admin_count() == 1:
                form.is_admin.errors.append("Cannot demote the last admin user.")
                return _render_user_form(
                    form,
                    target_user=user,
                    pet_items_by_type=pet_items_by_type,
                    pet_errors=pet_error_messages,
                )
            user.is_admin = form.is_admin.data
            user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        try:
            _sync_user_pets(user, pet_items_by_type)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            pet_error_messages.append(str(exc))
        except IntegrityError:
            db.session.rollback()
            form.login_name.errors.append("That login name, person, or pet assignment already exists.")
        else:
            flash("User updated.", "success")
            return redirect(
                url_for("users.list_users" if current_user.is_admin else "main.dashboard")
            )

    return _render_user_form(
        form,
        target_user=user,
        pet_items_by_type=pet_items_by_type,
        pet_errors=pet_error_messages,
    )


@users_bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id: int):
    require_admin()

    user = db.get_or_404(AppUser, user_id)
    other_admin_count = AppUser.query.filter(
        AppUser.is_admin.is_(True),
        AppUser.id != user.id,
    ).count()

    if user.is_admin and other_admin_count == 0:
        flash("Cannot delete the last admin user.", "danger")
        return redirect(url_for("users.list_users"))
    if user.id == current_user.id and other_admin_count == 0:
        flash("Cannot delete the currently logged-in user unless another admin remains.", "danger")
        return redirect(url_for("users.list_users"))

    try:
        db.session.query(HostAssignment).filter(HostAssignment.user_id == user.id).update(
            {HostAssignment.user_id: None},
            synchronize_session=False,
        )
        db.session.delete(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Could not delete the user because related records still exist.", "danger")
        return redirect(url_for("users.list_users"))
    flash("User deleted.", "success")
    return redirect(url_for("users.list_users"))


def _admin_count() -> int:
    return AppUser.query.filter_by(is_admin=True).count()


def _submitted_pet_items_by_type() -> tuple[dict[str, list[str]], list[str]]:
    production_pets, production_errors = parse_unique_fqdn_lines(request.form.get("production_pet_blob"))
    non_production_pets, non_production_errors = parse_unique_fqdn_lines(
        request.form.get("non_production_pet_blob")
    )
    return {
        PET_TYPE_PRODUCTION: production_pets,
        PET_TYPE_NON_PRODUCTION: non_production_pets,
    }, production_errors + non_production_errors


def _render_user_form(
    form: UserForm,
    target_user: AppUser | None,
    pet_items_by_type: dict[str, list[str]],
    pet_errors: list[str] | None = None,
):
    form.production_pet_blob.data = "\n".join(pet_items_by_type[PET_TYPE_PRODUCTION])
    form.non_production_pet_blob.data = "\n".join(pet_items_by_type[PET_TYPE_NON_PRODUCTION])
    return render_template(
        "user_form.html",
        form=form,
        target_user=target_user,
        production_pet_items=pet_items_by_type[PET_TYPE_PRODUCTION],
        non_production_pet_items=pet_items_by_type[PET_TYPE_NON_PRODUCTION],
        pet_blob_errors=pet_errors or [],
    )


def _current_pet_items_by_type(user: AppUser) -> dict[str, list[str]]:
    return {
        PET_TYPE_PRODUCTION: [pet.fqdn for pet in user.pets if pet.pet_type == PET_TYPE_PRODUCTION],
        PET_TYPE_NON_PRODUCTION: [
            pet.fqdn for pet in user.pets if pet.pet_type == PET_TYPE_NON_PRODUCTION
        ],
    }


def _sync_user_pets(user: AppUser, pet_fqdns_by_type: dict[str, list[str]]) -> None:
    desired_by_type = {
        PET_TYPE_PRODUCTION: pet_fqdns_by_type.get(PET_TYPE_PRODUCTION, []),
        PET_TYPE_NON_PRODUCTION: pet_fqdns_by_type.get(PET_TYPE_NON_PRODUCTION, []),
    }
    if not desired_by_type[PET_TYPE_PRODUCTION] and not desired_by_type[PET_TYPE_NON_PRODUCTION]:
        user.pets[:] = []
        return

    existing = {(pet.pet_type, pet.fqdn): pet for pet in user.pets}
    for pet_type, pet_fqdns in desired_by_type.items():
        if not pet_fqdns:
            continue
        conflicting_pet = (
            PetHost.query.filter(
                PetHost.pet_type == pet_type,
                PetHost.fqdn.in_(pet_fqdns),
                PetHost.user_id != user.id,
            )
            .order_by(PetHost.fqdn)
            .first()
        )
        if conflicting_pet is not None:
            owner_name = (
                conflicting_pet.owner.display_name
                if conflicting_pet.owner is not None
                else "another user"
            )
            raise ValueError(
                f"{pet_type_label(pet_type)} pet {conflicting_pet.fqdn} is already assigned to {owner_name}."
            )

    desired_pets: list[PetHost] = []
    for pet_type in (PET_TYPE_PRODUCTION, PET_TYPE_NON_PRODUCTION):
        for fqdn in desired_by_type[pet_type]:
            current_pet = existing.get((pet_type, fqdn))
            if current_pet is not None:
                desired_pets.append(current_pet)
            else:
                desired_pets.append(PetHost(fqdn=fqdn, pet_type=pet_type))
    user.pets[:] = desired_pets
