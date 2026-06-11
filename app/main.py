from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import tempfile
from typing import Any

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db
from .permissions import require_admin
from .models import (
    AppUser,
    AssignmentRun,
    PET_TYPE_NON_PRODUCTION,
    PET_TYPE_PRODUCTION,
    PetHost,
)
from .services.assignment_persistence import generate_and_persist_assignment
from .services.exporter import ExportError, export_assignment_run_to_zip
from .services.forekat_client import ForeKatClient, ForeKatClientError
from .services.host_exclusions import (
    get_host_exclusion_text,
    parse_host_exclusion_lines,
    replace_host_exclusions,
)
from .services.host_inventory import get_inventory_snapshot


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    schema_warning = None
    latest_run = None
    if _assignment_run_schema_ready():
        latest_run = AssignmentRun.query.order_by(AssignmentRun.id.desc()).first()
    else:
        schema_warning = (
            "Assignment history is temporarily unavailable until the database schema is upgraded. "
            "Run flask --app run.py db upgrade."
    )
    return render_template("dashboard.html", latest_run=latest_run, schema_warning=schema_warning)


@main_bp.route("/documentation")
@login_required
def documentation():
    return render_template(
        "documentation.html",
        assignment_config=current_app.assignment_config,
    )


@main_bp.route("/forekat/test", methods=["GET", "POST"])
@login_required
def forekat_test():
    if request.method == "GET":
        return render_template(
            "loading.html",
            page_title="ForeKat Test",
            heading="ForeKat Connectivity Test",
            message="Retrieving data from ForeKat...",
            continue_label="Continue to ForeKat Test",
            action_url=url_for("main.forekat_test"),
            action_description="A quick connectivity check against the live ForeKat API.",
        )

    status: dict | None = None
    warnings: list[str] = []
    try:
        client = ForeKatClient(current_app.forekat_config)
        inventory = get_inventory_snapshot(client)
        status = {
            "host_count": len(inventory["all_hosts"]),
        }
        warnings = inventory["warnings"]
    except ForeKatClientError as exc:
        status = {"error": str(exc)}
    return render_template("forekat_test.html", status=status, warnings=warnings)


@main_bp.route("/hosts", methods=["GET", "POST"])
@login_required
def hosts():
    hosts_data: list[dict] = []
    warnings: list[str] = []
    total_hosts = 0
    if request.method == "POST":
        try:
            client = ForeKatClient(current_app.forekat_config)
            inventory = get_inventory_snapshot(client)
            hosts_data = _build_host_rows(inventory)
            warnings = inventory["warnings"]
            total_hosts = len(hosts_data)
        except ForeKatClientError as exc:
            flash(str(exc), "danger")
    return render_template("hosts.html", hosts=hosts_data, warnings=warnings, total_hosts=total_hosts)


@main_bp.route("/hosts/exclusions", methods=["GET", "POST"])
@login_required
def host_exclusions():
    exclusions_text = get_host_exclusion_text()
    validation_errors: list[str] = []
    if request.method == "POST":
        require_admin()
        submitted_text = str(request.form.get("host_exclusions", ""))
        exclusions, validation_errors = parse_host_exclusion_lines(submitted_text)
        exclusions_text = submitted_text
        if not validation_errors:
            try:
                replace_host_exclusions(exclusions, current_user.id)
                db.session.commit()
            except Exception:
                db.session.rollback()
                current_app.logger.exception("Failed to save host exclusions")
                flash("Failed to save host exclusions.", "danger")
            else:
                flash(f"Saved {len(exclusions)} host exclusion(s).", "success")
                return redirect(url_for("main.host_exclusions"))

    return render_template(
        "host_exclusions.html",
        exclusions_text=exclusions_text,
        validation_errors=validation_errors,
        can_edit=current_user.is_admin,
    )


@main_bp.route("/pets")
@login_required
def pets():
    users = AppUser.query.order_by(AppUser.first_name, AppUser.last_name).all()
    return render_template("pets.html", users=users)


@main_bp.route("/assignments")
@login_required
def assignments():
    return redirect(url_for("main.latest_assignment"))


@main_bp.route("/assignments/latest")
@login_required
def latest_assignment():
    if not _assignment_run_schema_ready():
        flash(
            "Assignment history is unavailable until the database schema is upgraded. Run flask --app run.py db upgrade.",
            "danger",
        )
        return redirect(url_for("main.dashboard"))
    latest_run = AssignmentRun.query.order_by(AssignmentRun.id.desc()).first()
    if latest_run is None:
        flash("No assignment run has been generated yet.", "info")
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.view_assignment", run_id=latest_run.id))


@main_bp.route("/assignments/generate", methods=["GET", "POST"])
@main_bp.route("/assignments/generate/<pool_name>", methods=["GET", "POST"])
@login_required
def generate_assignments(pool_name: str | None = None):
    require_admin()

    normalized_pool = _normalize_pool_name(pool_name) if pool_name else None
    if pool_name and normalized_pool not in {"production", "non_production"}:
        flash("Unknown host pool requested for assignment generation.", "danger")
        return redirect(url_for("main.dashboard"))

    if request.method == "GET":
        if normalized_pool == "production":
            pool_label = "Production"
        elif normalized_pool == "non_production":
            pool_label = "Non-Production"
        else:
            pool_label = "Assignment"
        return render_template(
            "loading.html",
            page_title="Generate Assignment",
            heading=f"Generate {pool_label}",
            message=(
                f"Retrieving data and generating the {pool_label.lower()} host assignment..."
                if normalized_pool in {"production", "non_production"}
                else "Retrieving data and generating the current host assignment..."
            ),
            continue_label=(
                f"Continue to generate {pool_label} hosts assignment"
                if normalized_pool in {"production", "non_production"}
                else "Continue to generate assignment"
            ),
            action_url=url_for("main.generate_assignments", pool_name=pool_name),
            action_description="This will run the synchronous ForeKat inventory and balancing workflow.",
        )

    try:
        run = generate_and_persist_assignment(current_user.id, pool_name=normalized_pool)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.dashboard"))
    except ForeKatClientError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.dashboard"))
    except Exception as exc:  # pragma: no cover - network path
        current_app.logger.exception("Assignment generation failed")
        flash("Failed to generate assignments. Check the dashboard warnings and try again.", "danger")
        return redirect(url_for("main.dashboard"))
    flash("Assignment run generated.", "success")
    return redirect(url_for("main.view_assignment", run_id=run.id))


@main_bp.route("/assignments/<int:run_id>")
@login_required
def view_assignment(run_id: int):
    if not _assignment_run_schema_ready():
        flash(
            "Assignment details are unavailable until the database schema is upgraded. Run flask --app run.py db upgrade.",
            "danger",
        )
        return redirect(url_for("main.dashboard"))
    latest_run = AssignmentRun.query.get_or_404(run_id)
    assignment_context = _build_assignment_detail(latest_run)
    return render_template("assignments.html", **assignment_context)


@main_bp.route("/assignments/<int:run_id>/export", methods=["POST"])
@login_required
def export_assignment_run(run_id: int):
    require_admin()
    if not _assignment_run_schema_ready():
        flash(
            "Assignment export is unavailable until the database schema is upgraded. Run flask --app run.py db upgrade.",
            "danger",
        )
        return redirect(url_for("main.view_assignment", run_id=run_id))

    latest_run = AssignmentRun.query.get_or_404(run_id)
    change_request_number = str(request.form.get("change_request_number", "")).strip()
    if not change_request_number:
        flash("Change Request Number is required.", "danger")
        return redirect(url_for("main.view_assignment", run_id=latest_run.id))

    temp_export_dir = tempfile.TemporaryDirectory(prefix=f"assignment-run-{latest_run.id}-")
    template_path = Path(current_app.root_path).parent / "TEMPLATE - Patching run tracking and logging.xltx"
    try:
        export_result = export_assignment_run_to_zip(
            latest_run.id,
            change_request_number,
            temp_export_dir.name,
            template_path=template_path,
        )
    except ExportError as exc:
        temp_export_dir.cleanup()
        flash(str(exc), "danger")
        return redirect(url_for("main.view_assignment", run_id=latest_run.id))
    except Exception:
        temp_export_dir.cleanup()
        current_app.logger.exception("Failed to export assignment run %s", latest_run.id)
        flash("Failed to export assignment run.", "danger")
        return redirect(url_for("main.view_assignment", run_id=latest_run.id))

    response = send_file(
        export_result.zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=export_result.zip_filename,
        conditional=True,
    )
    response.call_on_close(temp_export_dir.cleanup)
    return response


def _build_assignment_rows(latest_run: AssignmentRun | None) -> list[dict]:
    rows = []
    users = AppUser.query.order_by(AppUser.first_name, AppUser.last_name).all()
    assigned_by_user: dict[int, list[str]] = {}
    if latest_run is not None:
        for item in latest_run.assignments:
            assigned_by_user.setdefault(item.user_id, []).append(item.fqdn)

    for user in users:
        pets = _pets_for_pool(user, latest_run.pool_name if latest_run is not None else None)
        rows.append(
            {
                "user": user,
                "pets": pets["items"],
                "pet_label": pets["label"],
                "assigned_hosts": sorted(assigned_by_user.get(user.id, [])),
            }
        )
    return rows


def _build_assignment_detail(latest_run: AssignmentRun) -> dict:
    users = AppUser.query.order_by(AppUser.first_name, AppUser.last_name).all()
    assignments_by_user: dict[int, list] = defaultdict(list)
    for item in latest_run.assignments:
        assignments_by_user[item.user_id].append(item)

    assignment_rows: list[dict] = []
    assigned_counts: list[int] = []
    for user in users:
        user_assignments = sorted(assignments_by_user.get(user.id, []), key=lambda item: item.fqdn)
        assigned_counts.append(len(user_assignments))
        pets = _pets_for_pool(user, latest_run.pool_name)
        assignment_rows.append(
            {
                "user": user,
                "assignment_count": len(user_assignments),
                "pets": pets["items"],
                "pet_label": pets["label"],
                "assign_only_label": user.assign_only_label_for_pool(latest_run.pool_name),
                "assigned_hosts": [
                    _build_assigned_host_display(item) for item in user_assignments
                ],
            }
        )

    grouped_sections = _build_group_sections(latest_run)
    total_hosts_assigned = len(latest_run.assignments)
    min_assigned = min(assigned_counts) if assigned_counts else 0
    max_assigned = max(assigned_counts) if assigned_counts else 0
    return {
        "latest_run": latest_run,
        "pool_label": _pool_label(latest_run),
        "assignment_rows": assignment_rows,
        "warnings": [warning.message for warning in latest_run.warnings],
        "summary": {
            "total_hosts_assigned": total_hosts_assigned,
            "user_count": len(users),
            "min_assigned": min_assigned,
            "max_assigned": max_assigned,
            "difference": max_assigned - min_assigned,
            "excluded_host_count": int(getattr(latest_run, "excluded_host_count", 0) or 0),
        },
        "assignment_source_key": _assignment_source_key_items(),
        "prefix_sequence_groups": grouped_sections["prefix_sequence"],
    }


def _build_host_rows(inventory: dict) -> list[dict]:
    pet_map: dict[str, set[str]] = defaultdict(set)
    for pet in PetHost.query.join(AppUser).order_by(PetHost.fqdn, PetHost.pet_type).all():
        owner_name = pet.owner.display_name if pet.owner is not None else f"user-{pet.user_id}"
        pet_map[pet.fqdn].add(f"{owner_name} ({pet.pet_type_label})")
    rows = []
    for host in inventory["all_hosts"]:
        fqdn = host["fqdn"]
        rows.append(
            {
                "fqdn": fqdn,
                "foreman_id": host.get("id"),
                "pet_owner_name": ", ".join(sorted(pet_map.get(fqdn, set()))) or None,
            }
        )
    return rows


def _pets_for_pool(user: AppUser, pool_name: str | None) -> dict[str, list[str] | str]:
    normalized_pool = _normalize_pool_name(pool_name)
    if normalized_pool == "production":
        pets = [pet.fqdn for pet in user.pets if pet.pet_type == PET_TYPE_PRODUCTION]
        return {"label": "Production Pets", "items": pets}
    if normalized_pool == "non_production":
        pets = [pet.fqdn for pet in user.pets if pet.pet_type == PET_TYPE_NON_PRODUCTION]
        return {"label": "Non-Production Pets", "items": pets}
    return {"label": "Pets", "items": [pet.fqdn for pet in user.pets]}


def _build_group_sections(latest_run: AssignmentRun) -> dict[str, list[dict]]:
    grouped: dict[tuple[str, str | None], list] = defaultdict(list)
    for item in latest_run.assignments:
        if item.source_type != "prefix_sequence":
            continue
        grouped[(item.source_type, item.source_name)].append(item)

    sections: dict[str, list[dict]] = {"prefix_sequence": []}
    users_by_id = {user.id: user for user in AppUser.query.order_by(AppUser.id).all()}
    for (source_type, source_name), items in sorted(grouped.items(), key=lambda entry: (entry[0][0], entry[0][1] or "")):
        user_ids = sorted({item.user_id for item in items})
        assigned_user = users_by_id[user_ids[0]] if user_ids else None
        sections[source_type].append(
            {
                "source_name": source_name or "",
                "user_name": assigned_user.full_name if assigned_user else "",
                "hosts": [
                    _format_assigned_host(item.fqdn, item.source_type, item.source_name)
                    for item in sorted(items, key=lambda item: item.fqdn)
                ],
                "count": len(items),
            }
        )
    return sections


def _format_assigned_host(fqdn: str, source_type: str, source_name: str | None) -> str:
    if source_type == "prefix_sequence":
        return f"{fqdn} [prefix_sequence]"
    if source_name:
        return f"{fqdn} [{source_type}: {source_name}]"
    return f"{fqdn} [{source_type}]"


def _build_assigned_host_display(item: Any) -> dict[str, str]:
    source_type = str(getattr(item, "source_type", "") or "").strip().lower()
    source_name = getattr(item, "source_name", None)
    meta = _source_display_meta(source_type, source_name)
    title = meta["title"]
    if source_type == "prefix_sequence" and source_name:
        title = f"Prefix Sequence: {source_name}"
    elif source_type == "pet":
        title = "Pet"
    elif source_type == "random":
        title = "Random"
    elif source_type:
        title = f"Legacy source type: {source_type}"
    return {
        "fqdn": getattr(item, "fqdn", ""),
        "source_type": source_type or "unknown",
        "source_name": source_name or "",
        "source_css_class": meta["css_class"],
        "source_label": meta["label"],
        "source_aria_label": meta["aria_label"],
        "source_title": title,
    }


def _assignment_source_key_items() -> list[dict[str, str]]:
    return [
        _source_display_meta("random"),
        _source_display_meta("prefix_sequence"),
        _source_display_meta("pet"),
    ]


def _source_display_meta(source_type: str, source_name: str | None = None) -> dict[str, str]:
    normalized = str(source_type or "").strip().lower()
    if normalized == "random":
        return {
            "css_class": "source-dot-random",
            "label": "Random",
            "aria_label": "Random",
            "title": "Random",
        }
    if normalized == "prefix_sequence":
        title = "Prefix Sequence"
        if source_name:
            title = f"Prefix Sequence: {source_name}"
        return {
            "css_class": "source-dot-prefix-sequence",
            "label": "Prefix Sequence",
            "aria_label": "Prefix Sequence",
            "title": title,
        }
    if normalized == "pet":
        return {
            "css_class": "source-dot-pet",
            "label": "Pet",
            "aria_label": "Pet",
            "title": "Pet",
        }
    return {
        "css_class": "source-dot-unknown",
        "label": "Unknown",
        "aria_label": f"Unknown source type: {normalized or 'unknown'}",
        "title": normalized or "Unknown",
    }


def _pool_label(run: AssignmentRun) -> str:
    if run.pool_collection_name:
        return run.pool_collection_name
    if run.pool_name:
        normalized = run.pool_name.strip().lower()
        if normalized == "production":
            return "Production"
        if normalized == "non_production":
            return "Non-Production"
    return "Legacy/Unknown"


def _normalize_pool_name(pool_name: str | None) -> str | None:
    if pool_name is None:
        return None
    normalized = pool_name.strip().lower()
    if normalized in {"production", "non-production", "non_production"}:
        return "production" if normalized == "production" else "non_production"
    return normalized or None


def _assignment_run_schema_ready() -> bool:
    required_columns = {"pool_name", "pool_collection_name", "excluded_host_count"}
    try:
        from sqlalchemy import inspect as sa_inspect

        columns = {column["name"] for column in sa_inspect(db.engine).get_columns("assignment_runs")}
    except SQLAlchemyError:
        return False
    except Exception:  # pragma: no cover - defensive safety net
        current_app.logger.exception("Unable to inspect assignment run schema")
        return False
    return required_columns.issubset(columns)
