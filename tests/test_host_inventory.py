from __future__ import annotations

import pytest

from app.services.forekat_client import ForeKatClientError
from app.services.host_inventory import get_host_collection_name, get_hosts_for_assignment_pool, get_inventory_snapshot


class FakeClient:
    def __init__(self, hosts: list[dict], collections: list[dict]):
        self._hosts = hosts
        self._collections = collections
        self.host_calls = 0
        self.collection_calls = 0
        self.collection_detail_calls = 0

    def fetch_all_hosts(self):
        self.host_calls += 1
        return {
            "hosts": self._hosts,
            "warnings": ["host warning"],
            "metadata": [{"page": 1, "returned": len(self._hosts)}],
        }

    def fetch_host_collection_index(self):
        self.collection_calls += 1
        collection_index = [
            {key: value for key, value in collection.items() if key in {"id", "name", "total_hosts"}}
            for collection in self._collections
        ]
        return {
            "collections": collection_index,
            "warnings": ["collection warning"],
            "metadata": [{"page": 1, "returned": len(self._collections)}],
        }

    def fetch_host_collection_detail(self, collection_id):
        self.collection_detail_calls += 1
        for collection in self._collections:
            if collection.get("id") == collection_id:
                return {
                    "collection": collection,
                    "warnings": [],
                }
        raise ForeKatClientError(f"Missing detail for collection id {collection_id}.")

    def fetch_host_collections(self):
        self.collection_calls += 1
        return {
            "collections": self._collections,
            "warnings": ["collection warning"],
            "metadata": [{"page": 1, "returned": len(self._collections)}],
        }


def _host(host_id: int, fqdn: str) -> dict:
    return {"id": host_id, "fqdn": fqdn}


def test_get_inventory_snapshot_deduplicates_hosts_and_avoids_host_collections():
    client = FakeClient(
        hosts=[
            _host(1, "host01.example.com"),
            _host(2, "HOST01.EXAMPLE.COM".lower()),
            _host(3, "host02.example.com"),
        ],
        collections=[],
    )

    snapshot = get_inventory_snapshot(client)

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == [
        "host01.example.com",
        "host02.example.com",
    ]
    assert snapshot["warnings"] == ["host warning"]
    assert client.collection_calls == 0


def test_get_hosts_for_assignment_pool_filters_production_hosts():
    client = FakeClient(
        hosts=[
            _host(1, "prod01.example.com"),
            _host(2, "prod02.example.com"),
            _host(3, "dev01.example.com"),
        ],
        collections=[
            {"id": 10, "name": "Production", "host_ids": [1, 2]},
            {"id": 11, "name": "Non-Production", "host_ids": [3]},
        ],
    )

    snapshot = get_hosts_for_assignment_pool(client, "production")

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == [
        "prod01.example.com",
        "prod02.example.com",
    ]
    assert snapshot["pool_name"] == "production"
    assert snapshot["collection_name"] == "Production"
    assert snapshot["total_all_foreman_hosts"] == 3
    assert snapshot["filtered_host_count"] == 2
    assert client.collection_calls == 1
    assert client.collection_detail_calls == 1


def test_get_hosts_for_assignment_pool_uses_collection_index_for_matching():
    client = FakeClient(
        hosts=[
            _host(1, "prod01.example.com"),
            _host(2, "prod02.example.com"),
        ],
        collections=[
            {"id": 10, "name": "Production", "host_ids": [1, 2]},
        ],
    )

    snapshot = get_hosts_for_assignment_pool(client, "production")

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == [
        "prod01.example.com",
        "prod02.example.com",
    ]
    assert snapshot["collection_name"] == "Production"


def test_get_hosts_for_assignment_pool_filters_non_production_hosts():
    client = FakeClient(
        hosts=[
            _host(1, "prod01.example.com"),
            _host(2, "prod02.example.com"),
            _host(3, "dev01.example.com"),
        ],
        collections=[
            {"id": 10, "name": "Production", "host_ids": [1, 2]},
            {"id": 11, "name": "Non-Production", "host_ids": [3]},
        ],
    )

    snapshot = get_hosts_for_assignment_pool(client, "non-production")

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == ["dev01.example.com"]
    assert snapshot["pool_name"] == "non_production"
    assert snapshot["collection_name"] == "Non-Production"


def test_get_hosts_for_assignment_pool_maps_host_ids_to_fqdns():
    client = FakeClient(
        hosts=[
            _host(1, "prod01.example.com"),
            _host(2, "prod02.example.com"),
        ],
        collections=[
            {
                "id": 10,
                "name": "Production",
                "host_ids": [1],
                "host_fqdns": [],
                "raw": {"host_ids": [1]},
            }
        ],
    )

    snapshot = get_hosts_for_assignment_pool(client, "production")

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == ["prod01.example.com"]


def test_get_hosts_for_assignment_pool_warns_on_unmapped_members():
    client = FakeClient(
        hosts=[_host(1, "prod01.example.com")],
        collections=[
            {
                "id": 10,
                "name": "Production",
                "host_ids": [1, 999],
                "host_fqdns": ["prod01.example.com", "missing.example.com"],
                "raw": {"host_ids": [1, 999]},
            }
        ],
    )

    snapshot = get_hosts_for_assignment_pool(client, "production")

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == ["prod01.example.com"]
    assert any("missing.example.com" in warning for warning in snapshot["warnings"])
    assert any("999" in warning for warning in snapshot["warnings"])


def test_get_hosts_for_assignment_pool_raises_when_collection_missing():
    client = FakeClient(
        hosts=[_host(1, "prod01.example.com")],
        collections=[{"id": 11, "name": "Non-Production", "host_ids": [1]}],
    )

    with pytest.raises(ForeKatClientError, match="Production"):
        get_hosts_for_assignment_pool(client, "production")


def test_get_hosts_for_assignment_pool_raises_when_collection_empty():
    client = FakeClient(
        hosts=[_host(1, "prod01.example.com")],
        collections=[{"id": 10, "name": "Production", "host_ids": []}],
    )

    with pytest.raises(ForeKatClientError, match="did not contain any hosts"):
        get_hosts_for_assignment_pool(client, "production")


def test_get_host_collection_name_returns_literal_names():
    assert get_host_collection_name("production") == "Production"
    assert get_host_collection_name("non_production") == "Non-Production"


def test_get_hosts_for_assignment_pool_tolerates_harmless_name_formatting():
    client = FakeClient(
        hosts=[
            _host(1, "prod01.example.com"),
        ],
        collections=[
            {"id": 10, "name": " Non_Production ", "host_ids": [1]},
        ],
    )

    snapshot = get_hosts_for_assignment_pool(client, "non-production")

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == ["prod01.example.com"]


def test_get_hosts_for_assignment_pool_accepts_punctuation_noise_in_collection_name():
    client = FakeClient(
        hosts=[_host(1, "prod01.example.com")],
        collections=[
            {"id": 10, "name": "Non - Production", "host_ids": [1]},
        ],
    )

    snapshot = get_hosts_for_assignment_pool(client, "non-production")

    assert [host["fqdn"] for host in snapshot["all_hosts"]] == ["prod01.example.com"]
