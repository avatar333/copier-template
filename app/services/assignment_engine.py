from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .assignment_helpers import build_prefix_sequence_group_details, least_loaded_user_id

SPECIAL_PREFIX_SEQUENCE_GROUPS = {
    "production": {
        "source_name": "jboss-production-special",
        "hosts": [
            "jboss01-prod-bry.platform.is",
            "jboss02-prod-pkl.platform.is",
            "jboss03-prod-bry.platform.is",
            "jboss04-prod-pkl.platform.is",
            "jboss05-prod-bry.platform.is",
            "jboss06-prod-pkl.platform.is",
        ],
    },
    "non_production": {
        "source_name": "jboss-non-production-special",
        "hosts": [
            "jboss01-dev-bry.platform.is",
            "jboss02-dev-pkl.platform.is",
            "jboss03-dev-bry.platform.is",
            "jboss04-dev-pkl.platform.is",
            "jboss05-dev-bry.platform.is",
            "jboss06-dev-pkl.platform.is",
        ],
    },
}


@dataclass(slots=True)
class AssignmentItem:
    fqdn: str
    source_type: str
    source_name: str | None = None


@dataclass(slots=True)
class AssignmentResult:
    assignments_by_user: dict[int, list[AssignmentItem]]
    warnings: list[str]
    all_available_hosts: list[str]
    remaining_unassigned_hosts: list[str]
    grouped_prefix_sequences: list[dict[str, Any]]
    error_message: str | None = None

    @property
    def has_error(self) -> bool:
        return self.error_message is not None


def _normalize_fqdn(value: Any) -> str | None:
    if value is None:
        return None
    fqdn = str(value).strip().lower()
    return fqdn or None


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _user_label(user: Any) -> str:
    login_name = _get_value(user, "login_name")
    if login_name:
        return str(login_name)
    first_name = str(_get_value(user, "first_name", "")).strip()
    last_name = str(_get_value(user, "last_name", "")).strip()
    label = f"{first_name} {last_name}".strip()
    return label or f"user-{_get_value(user, 'id')}"


def _user_id(user: Any) -> int:
    return int(_get_value(user, "id"))


def _assign_only_for_pool(user: Any, pool_name: str | None) -> bool:
    normalized_pool = _normalize_pool_name(pool_name)
    if normalized_pool == "production":
        return bool(_get_value(user, "assign_only_production_pets", False))
    if normalized_pool == "non_production":
        return bool(_get_value(user, "assign_only_non_production_pets", False))
    return bool(_get_value(user, "assign_only_pets", False))


def _assign_only_warning_for_pool(pool_name: str | None) -> str:
    normalized_pool = _normalize_pool_name(pool_name)
    if normalized_pool == "production":
        return "All users are marked Assign ONLY Production Pets; non-pet Production hosts were not assigned."
    if normalized_pool == "non_production":
        return (
            "All users are marked Assign ONLY Non-Production Pets; "
            "non-pet Non-Production hosts were not assigned."
        )
    return "All users are marked Assign ONLY Pets; non-pet hosts were not assigned."


def _pick_user(loads: dict[int, int], rng: random.Random, forced_user_id: int | None = None) -> int:
    if forced_user_id is not None:
        return forced_user_id
    return least_loaded_user_id(loads, rng)


def _pick_prefix_group_user(
    loads: dict[int, int],
    rng: random.Random,
    randomness_window: int,
    allowed_user_ids: list[int] | None = None,
) -> int | None:
    """Pick a user from a small balanced window.

    Prefix/sequence groups stay unsplittable, but this window lets us choose
    among nearly-equal users so the same host bundle does not always land on
    the exact same person.
    """
    if allowed_user_ids is None:
        candidate_loads = loads
    else:
        candidate_loads = {user_id: loads[user_id] for user_id in allowed_user_ids if user_id in loads}
    if not candidate_loads:
        return None
    minimum = min(candidate_loads.values())
    eligible = [
        user_id for user_id, load in candidate_loads.items() if load <= minimum + randomness_window
    ]
    return rng.choice(eligible or list(candidate_loads.keys()))


class AssignmentEngine:
    def __init__(
        self,
        users: Iterable[Any],
        all_hosts: Iterable[str],
        pet_map: Mapping[int, Iterable[str]],
        config: Mapping[str, Any],
        rng: random.Random | None = None,
        pool_name: str | None = None,
    ):
        self.users = sorted(list(users), key=_user_id)
        self.all_hosts = sorted({fqdn for fqdn in (_normalize_fqdn(host) for host in all_hosts) if fqdn})
        self.pet_map = {
            int(user_id): {
                fqdn
                for fqdn in (_normalize_fqdn(pet_fqdn) for pet_fqdn in pet_fqdns)
                if fqdn
            }
            for user_id, pet_fqdns in pet_map.items()
        }
        self.config = config
        assignment_config = config.get("assignment", config) if isinstance(config, Mapping) else config
        self.random_seed = _lookup_config_value(assignment_config, "random_seed")
        self.min_prefix_group_size = int(
            _lookup_config_value(assignment_config, "min_prefix_group_size", 2) or 2
        )
        raw_window = _lookup_config_value(assignment_config, "prefix_group_randomness_window", 1)
        self.prefix_group_randomness_window = max(0, int(raw_window if raw_window is not None else 1))
        self.pool_name = _normalize_pool_name(pool_name)
        self.assign_only_pets_user_ids = {
            _user_id(user)
            for user in self.users
            if _assign_only_for_pool(user, self.pool_name)
        }
        self.rng = rng or (random.Random(self.random_seed) if self.random_seed is not None else random.Random())

    def generate(self) -> AssignmentResult:
        """Run the full assignment pass.

        Pets are claimed first, then contiguous prefix/sequence runs, and
        finally any leftover hosts are distributed one by one to the currently
        least-loaded user.
        """
        all_hosts = list(self.all_hosts)
        warnings: list[str] = []
        assignments_by_user: dict[int, list[AssignmentItem]] = {
            _user_id(user): [] for user in self.users
        }
        grouped_prefix_sequences: list[dict[str, Any]] = []
        remaining_pool = set(all_hosts)
        blocked_hosts: set[str] = set()
        pet_assigned_hosts: set[str] = set()

        if not self.users:
            error = "No local users are available. Create at least one local user before generating assignments."
            return AssignmentResult(
                assignments_by_user={},
                warnings=[error],
                all_available_hosts=all_hosts,
                remaining_unassigned_hosts=all_hosts,
                grouped_prefix_sequences=[],
                error_message=error,
            )

        loads = {_user_id(user): 0 for user in self.users}
        if not all_hosts:
            warnings.append("No hosts were returned from Foreman.")

        eligible_non_pet_user_ids = [
            user_id for user_id in loads if user_id not in self.assign_only_pets_user_ids
        ]

        pet_owner_claims: dict[str, list[int]] = defaultdict(list)
        for user_id, pet_fqdns in self.pet_map.items():
            if user_id not in loads:
                continue
            for fqdn in pet_fqdns:
                pet_owner_claims[fqdn].append(user_id)

        for fqdn, user_ids in sorted(pet_owner_claims.items()):
            unique_user_ids = sorted(set(user_ids))
            if len(unique_user_ids) > 1:
                owner_names = ", ".join(_user_label(user) for user in self.users if _user_id(user) in unique_user_ids)
                warnings.append(
                    f"Pet host {fqdn} is claimed by multiple users: {owner_names}. It was left unassigned."
                )
                if fqdn in remaining_pool:
                    remaining_pool.remove(fqdn)
                    blocked_hosts.add(fqdn)
                continue

            owner_id = unique_user_ids[0]
            if fqdn not in remaining_pool:
                warnings.append(
                    f"Pet host {fqdn} for user {_user_label(_find_user(self.users, owner_id))} is not present in the available host inventory."
                )
                continue

            assignments_by_user[owner_id].append(AssignmentItem(fqdn=fqdn, source_type="pet", source_name=None))
            loads[owner_id] += 1
            remaining_pool.remove(fqdn)
            pet_assigned_hosts.add(fqdn)

        if remaining_pool and not eligible_non_pet_user_ids:
            warnings.append(_assign_only_warning_for_pool(self.pool_name))
            return AssignmentResult(
                assignments_by_user=assignments_by_user,
                warnings=warnings,
                all_available_hosts=all_hosts,
                remaining_unassigned_hosts=sorted(remaining_pool | blocked_hosts),
                grouped_prefix_sequences=grouped_prefix_sequences,
            )

        self._assign_special_prefix_sequence_groups(
            remaining_pool=remaining_pool,
            pet_assigned_hosts=pet_assigned_hosts,
            assignments_by_user=assignments_by_user,
            loads=loads,
            warnings=warnings,
            grouped_prefix_sequences=grouped_prefix_sequences,
            eligible_user_ids=eligible_non_pet_user_ids,
        )

        prefix_groups = [
            asdict(group)
            for group in build_prefix_sequence_group_details(
                list(remaining_pool),
                min_prefix_group_size=self.min_prefix_group_size,
            )
        ]
        prefix_groups = _order_groups_for_balanced_assignment(prefix_groups, self.rng)
        for group in prefix_groups:
            user_id = _pick_prefix_group_user(
                loads,
                self.rng,
                self.prefix_group_randomness_window,
                eligible_non_pet_user_ids,
            )
            if user_id is None:
                warnings.append(
                    f"Prefix sequence group {group['source_name']} could not be assigned because no eligible users were available."
                )
                continue
            group["assigned_user_id"] = user_id
            for fqdn in group["hosts"]:
                assignments_by_user[user_id].append(
                    AssignmentItem(fqdn=fqdn, source_type="prefix_sequence", source_name=group["source_name"])
                )
            loads[user_id] += len(group["hosts"])
            remaining_pool.difference_update(group["hosts"])
            grouped_prefix_sequences.append(group)

        random_hosts = sorted(remaining_pool)
        self.rng.shuffle(random_hosts)
        for fqdn in random_hosts:
            candidate_loads = {
                user_id: load for user_id, load in loads.items() if user_id in eligible_non_pet_user_ids
            }
            if not candidate_loads:
                warnings.append(f"Host {fqdn} could not be assigned because no eligible users were available.")
                continue
            user_id = least_loaded_user_id(candidate_loads, self.rng)
            assignments_by_user[user_id].append(AssignmentItem(fqdn=fqdn, source_type="random", source_name=None))
            loads[user_id] += 1
            remaining_pool.remove(fqdn)

        return AssignmentResult(
            assignments_by_user=assignments_by_user,
            warnings=warnings,
            all_available_hosts=all_hosts,
            remaining_unassigned_hosts=sorted(remaining_pool | blocked_hosts),
            grouped_prefix_sequences=grouped_prefix_sequences,
        )

    def _assign_special_prefix_sequence_groups(
        self,
        *,
        remaining_pool: set[str],
        pet_assigned_hosts: set[str],
        assignments_by_user: dict[int, list[AssignmentItem]],
        loads: dict[int, int],
        warnings: list[str],
        grouped_prefix_sequences: list[dict[str, Any]],
        eligible_user_ids: list[int],
    ) -> None:
        group_config = SPECIAL_PREFIX_SEQUENCE_GROUPS.get(self.pool_name or "")
        if group_config is None:
            return

        expected_hosts = list(group_config["hosts"])
        source_name = str(group_config["source_name"])
        selected_pool_hosts = set(self.all_hosts)
        present_hosts = [host for host in expected_hosts if host in selected_pool_hosts]
        if not present_hosts:
            return

        missing_hosts = [host for host in expected_hosts if host not in selected_pool_hosts]
        if missing_hosts:
            warnings.append(
                f"Special JBoss group {source_name} is missing expected hosts from the selected pool: "
                + ", ".join(missing_hosts)
            )

        pet_hosts = [host for host in present_hosts if host in pet_assigned_hosts]
        assignable_hosts = [host for host in present_hosts if host in remaining_pool]
        if pet_hosts:
            warnings.append(
                f"Special JBoss group {source_name} was partially split because pet ownership takes priority for: "
                + ", ".join(pet_hosts)
            )

        if not assignable_hosts:
            return

        user_id = _pick_prefix_group_user(
            loads,
            self.rng,
            self.prefix_group_randomness_window,
            eligible_user_ids,
        )
        if user_id is None:
            warnings.append(
                f"Special JBoss group {source_name} could not be assigned because no eligible users were available."
            )
            return
        group = {
            "group_key": source_name,
            "hosts": assignable_hosts,
            "sequence_numbers": [],
            "token_index": None,
            "source_name": source_name,
            "assigned_user_id": user_id,
        }
        for fqdn in assignable_hosts:
            assignments_by_user[user_id].append(
                AssignmentItem(fqdn=fqdn, source_type="prefix_sequence", source_name=source_name)
            )
        loads[user_id] += len(assignable_hosts)
        remaining_pool.difference_update(assignable_hosts)
        grouped_prefix_sequences.append(group)


def _order_groups_for_balanced_assignment(
    groups: list[dict[str, Any]],
    rng: random.Random,
    size_key: str = "hosts",
) -> list[dict[str, Any]]:
    groups_by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        if size_key == "hosts":
            group_size = len(group["hosts"])
        else:
            group_size = int(group.get(size_key, 0))
        groups_by_size[group_size].append(group)

    ordered: list[dict[str, Any]] = []
    for size in sorted(groups_by_size.keys(), reverse=True):
        bucket = groups_by_size[size]
        rng.shuffle(bucket)
        ordered.extend(bucket)
    return ordered


def _find_user(users: list[Any], user_id: int) -> Any:
    for user in users:
        if _user_id(user) == user_id:
            return user
    raise KeyError(user_id)


def _normalize_pool_name(pool_name: str | None) -> str | None:
    if pool_name is None:
        return None
    normalized = pool_name.strip().lower()
    if normalized in {"production", "non-production", "non_production"}:
        return "production" if normalized == "production" else "non_production"
    return normalized or None


def _lookup_config_value(config: Any, key: str, default: Any = None) -> Any:
    if isinstance(config, Mapping):
        return config.get(key, default)
    return getattr(config, key, default)
