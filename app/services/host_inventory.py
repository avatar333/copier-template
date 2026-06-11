from __future__ import annotations

import re
import unicodedata
from typing import Any

from .forekat_client import ForeKatClient, ForeKatClientError

POOL_COLLECTION_NAMES = {
    "production": "Production",
    "non_production": "Non-Production",
}


def get_inventory_snapshot(client: ForeKatClient, collection_filter: str | None = None) -> dict[str, Any]:
    if collection_filter is None:
        return _build_unfiltered_snapshot(client)
    return get_hosts_for_assignment_pool(client, collection_filter)


def get_hosts_for_assignment_pool(client: ForeKatClient, pool_name: str) -> dict[str, Any]:
    normalized_pool = _normalize_pool_name(pool_name)
    collection_name = get_host_collection_name(normalized_pool)
    if collection_name is None:
        raise ValueError(f"Unsupported host pool '{pool_name}'.")

    host_result = client.fetch_all_hosts()
    all_hosts = _deduplicate_hosts(host_result["hosts"])
    host_by_id = {host["id"]: host["fqdn"] for host in all_hosts if host.get("id") is not None}
    host_by_fqdn = {host["fqdn"]: host for host in all_hosts}

    collection_index_result = client.fetch_host_collection_index()
    warnings = list(host_result["warnings"]) + list(collection_index_result["warnings"])
    collection_index = collection_index_result["collections"]
    target_collection = _find_collection(collection_index, collection_name)
    if target_collection is None:
        available_names = ", ".join(
            sorted(
                str(collection.get("name", "")).strip()
                for collection in collection_index
                if str(collection.get("name", "")).strip()
            )
        )
        if available_names:
            suffix = f" Available collections: {available_names}."
        else:
            suffix = ""
        raise ForeKatClientError(f"Katello host collection '{collection_name}' was not found.{suffix}")

    target_collection_id = target_collection.get("id")
    if target_collection_id is None:
        raise ForeKatClientError(
            f"Katello host collection '{collection_name}' was found but did not include an id."
        )
    detail_result = client.fetch_host_collection_detail(target_collection_id)
    warnings.extend(detail_result["warnings"])
    detailed_collection = detail_result["collection"]
    if not detailed_collection.get("name"):
        detailed_collection["name"] = str(target_collection.get("name") or collection_name).strip()

    filtered_fqdns, pool_warnings = _resolve_collection_hosts(
        detailed_collection,
        host_by_id=host_by_id,
        host_by_fqdn=host_by_fqdn,
        collection_name=collection_name,
    )
    warnings.extend(pool_warnings)

    filtered_hosts = [host for host in all_hosts if host["fqdn"] in filtered_fqdns]
    if not filtered_hosts:
        raise ForeKatClientError(
            f"Katello host collection '{collection_name}' did not contain any hosts that could be used for assignments."
        )

    return {
        "all_foreman_hosts": all_hosts,
        "all_hosts": filtered_hosts,
        "available_hosts": filtered_hosts,
        "pool_name": normalized_pool,
        "collection_name": collection_name,
        "total_all_foreman_hosts": len(all_hosts),
        "filtered_host_count": len(filtered_hosts),
        "warnings": warnings,
        "metadata": {
            "foreman": host_result["metadata"],
            "katello": collection_index_result["metadata"],
        },
    }


def _build_unfiltered_snapshot(client: ForeKatClient) -> dict[str, Any]:
    host_result = client.fetch_all_hosts()
    deduplicated_hosts = _deduplicate_hosts(host_result["hosts"])
    return {
        "all_foreman_hosts": deduplicated_hosts,
        "all_hosts": deduplicated_hosts,
        "available_hosts": deduplicated_hosts,
        "pool_name": None,
        "collection_name": None,
        "total_all_foreman_hosts": len(deduplicated_hosts),
        "filtered_host_count": len(deduplicated_hosts),
        "warnings": host_result["warnings"],
        "metadata": host_result["metadata"],
    }


def _deduplicate_hosts(hosts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated_hosts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for host in hosts:
        fqdn = str(host["fqdn"]).lower()
        if fqdn in seen:
            continue
        seen.add(fqdn)
        normalized_host = dict(host)
        normalized_host["fqdn"] = fqdn
        deduplicated_hosts.append(normalized_host)
    return deduplicated_hosts


def _find_collection(collections: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    target = _normalize_collection_name(name)
    for collection in collections:
        if _normalize_collection_name(collection.get("name", "")) == target:
            return collection
    return None


def _resolve_collection_hosts(
    collection: dict[str, Any],
    *,
    host_by_id: dict[Any, str],
    host_by_fqdn: dict[str, dict[str, Any]],
    collection_name: str,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    filtered_fqdns: list[str] = []
    seen: set[str] = set()
    missing_ids: list[int] = []
    missing_fqdns: list[str] = []

    for fqdn in collection.get("host_fqdns", []) or []:
        normalized = str(fqdn).strip().lower()
        if not normalized:
            continue
        if normalized in host_by_fqdn and normalized not in seen:
            seen.add(normalized)
            filtered_fqdns.append(normalized)
        elif normalized not in host_by_fqdn:
            missing_fqdns.append(normalized)

    for host_id in collection.get("host_ids", []) or []:
        mapped = host_by_id.get(host_id)
        if mapped and mapped not in seen:
            seen.add(mapped)
            filtered_fqdns.append(mapped)
        elif mapped is None:
            try:
                missing_ids.append(int(host_id))
            except (TypeError, ValueError):
                continue

    if missing_fqdns:
        warnings.append(
            f"Katello host collection {collection_name} included hosts that were not present in the Foreman inventory: "
            + ", ".join(sorted(missing_fqdns))
        )
    if missing_ids:
        warnings.append(
            f"Katello host collection {collection_name} included host IDs that could not be mapped to Foreman hosts: "
            + ", ".join(str(value) for value in sorted(set(missing_ids)))
        )
    if not filtered_fqdns:
        warnings.append(f"Katello host collection {collection_name} did not contain any mapped hosts.")

    return filtered_fqdns, warnings


def _normalize_pool_name(pool_name: str) -> str:
    normalized = str(pool_name).strip().lower()
    if normalized in {"production", "non-production", "non_production"}:
        return "production" if normalized == "production" else "non_production"
    return normalized


def get_host_collection_name(pool_name: str) -> str | None:
    normalized_pool = _normalize_pool_name(pool_name)
    return POOL_COLLECTION_NAMES.get(normalized_pool)


def _normalize_collection_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    return re.sub(r"[^a-z0-9]+", "", text)
