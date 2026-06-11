from __future__ import annotations

from collections import defaultdict
from typing import Any

from flask import current_app

from ..extensions import db
from ..models import (
    AppUser,
    AssignmentRun,
    AssignmentWarning,
    HostAssignment,
    PET_TYPE_NON_PRODUCTION,
    PET_TYPE_PRODUCTION,
    PetHost,
    pet_type_label,
)
from .assignment_engine import AssignmentEngine, SPECIAL_PREFIX_SEQUENCE_GROUPS
from .forekat_client import ForeKatClient
from .host_exclusions import get_excluded_host_fqdns
from .host_inventory import get_hosts_for_assignment_pool, get_inventory_snapshot


def generate_and_persist_assignment(
    current_user_id: int | None,
    pool_name: str | None = None,
    client: ForeKatClient | None = None,
    rng: Any | None = None,
) -> AssignmentRun:
    client = client or ForeKatClient(current_app.forekat_config)
    inventory = (
        get_hosts_for_assignment_pool(client, pool_name)
        if pool_name is not None
        else get_inventory_snapshot(client)
    )

    users = AppUser.query.filter_by(is_active=True).order_by(AppUser.id).all()
    if not users:
        raise ValueError(
            "No local users are available. Create at least one local user before generating assignments."
        )
    pet_map: dict[int, set[str]] = defaultdict(set)
    selected_pool_hosts = inventory.get("available_hosts") or inventory.get("all_hosts") or []
    selected_hosts = {host["fqdn"] for host in selected_pool_hosts}
    foreman_hosts_source = inventory.get("all_foreman_hosts") or inventory.get("all_hosts") or []
    foreman_hosts = {host["fqdn"] for host in foreman_hosts_source}
    collection_name = inventory.get("collection_name") or pool_name or "Unknown"
    warnings = list(inventory.get("warnings", []))
    selected_pet_types = _selected_pet_types(inventory.get("pool_name"))
    if inventory.get("collection_name") is not None and not selected_hosts:
        raise ValueError(
            f"Katello host collection {collection_name} did not contain any hosts for assignment."
        )

    excluded_hosts = get_excluded_host_fqdns()
    excluded_pool_hosts = sorted(host["fqdn"] for host in selected_pool_hosts if host["fqdn"] in excluded_hosts)
    if excluded_pool_hosts:
        special_jboss_hosts = {
            host
            for group in SPECIAL_PREFIX_SEQUENCE_GROUPS.values()
            for host in group["hosts"]
        }
        for fqdn in excluded_pool_hosts:
            if fqdn in special_jboss_hosts:
                warnings.append(f"Special JBoss host {fqdn} is excluded and was not assigned.")
            else:
                warnings.append(f"Host {fqdn} is excluded and was not assigned.")
        warnings.append(
            f"Excluded hosts removed from the selected {collection_name} pool before assignment: "
            + ", ".join(excluded_pool_hosts)
        )

    filtered_pool_hosts = [host for host in selected_pool_hosts if host["fqdn"] not in excluded_hosts]
    filtered_selected_hosts = {host["fqdn"] for host in filtered_pool_hosts}
    all_selected_hosts_excluded = bool(selected_pool_hosts) and not filtered_pool_hosts and bool(excluded_pool_hosts)

    pet_query = PetHost.query.order_by(PetHost.user_id, PetHost.pet_type, PetHost.fqdn)
    if selected_pet_types is not None:
        pet_query = pet_query.filter(PetHost.pet_type.in_(selected_pet_types))
    for pet in pet_query.all():
        owner = pet.owner
        owner_label = owner.display_name if owner is not None else f"user-{pet.user_id}"
        fqdn = pet.fqdn.lower()
        pet_label = pet_type_label(pet.pet_type)
        if fqdn in excluded_hosts:
            warnings.append(f"Pet host {fqdn} for {owner_label} is excluded and was not assigned.")
            continue
        if fqdn not in foreman_hosts:
            warnings.append(
                f"{pet_label} pet host {fqdn} for {owner_label} is not present in Foreman and was not assigned."
            )
            continue
        if pool_name is not None and fqdn not in filtered_selected_hosts:
            warnings.append(
                f"{pet_label} pet host {fqdn} for {owner_label} is not part of the selected {collection_name} pool and was not assigned."
            )
            continue
        pet_map[pet.user_id].add(fqdn)

    if all_selected_hosts_excluded:
        warnings.append(f"All hosts in the selected {collection_name} pool are excluded.")

    if all_selected_hosts_excluded:
        run = AssignmentRun(
            created_by_user_id=current_user_id,
            pool_name=inventory.get("pool_name"),
            pool_collection_name=inventory.get("collection_name"),
            excluded_host_count=len(excluded_pool_hosts),
            host_count=0,
            user_count=len(users),
        )
        try:
            db.session.add(run)
            db.session.flush()
            for warning in warnings:
                db.session.add(AssignmentWarning(assignment_run_id=run.id, message=warning))
            db.session.commit()
            return run
        except Exception:
            db.session.rollback()
            raise

    engine = AssignmentEngine(
        users=users,
        all_hosts=[host["fqdn"] for host in filtered_pool_hosts],
        pet_map=pet_map,
        config=current_app.assignment_config,
        rng=rng,
        pool_name=inventory.get("pool_name"),
    )
    result = engine.generate()
    if result.has_error:
        raise ValueError(result.error_message or "Assignment generation failed.")

    run = AssignmentRun(
        created_by_user_id=current_user_id,
        pool_name=inventory.get("pool_name"),
        pool_collection_name=inventory.get("collection_name"),
        excluded_host_count=len(excluded_pool_hosts),
        host_count=len(result.all_available_hosts),
        user_count=len(users),
    )
    try:
        db.session.add(run)
        db.session.flush()
        for user_id, items in result.assignments_by_user.items():
            for item in items:
                db.session.add(
                    HostAssignment(
                        assignment_run_id=run.id,
                        user_id=user_id,
                        fqdn=item.fqdn,
                        source_type=item.source_type,
                        source_name=item.source_name,
                    )
                )
        for warning in result.warnings:
            db.session.add(AssignmentWarning(assignment_run_id=run.id, message=warning))
        for warning in warnings:
            db.session.add(AssignmentWarning(assignment_run_id=run.id, message=warning))
        db.session.commit()
        return run
    except Exception:
        db.session.rollback()
        raise


def _selected_pet_types(pool_name: str | None) -> tuple[str, ...] | None:
    if pool_name == "production":
        return (PET_TYPE_PRODUCTION,)
    if pool_name == "non_production":
        return (PET_TYPE_NON_PRODUCTION,)
    return None
