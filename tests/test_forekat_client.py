from __future__ import annotations

import pytest
import requests

from app.services.forekat_client import ForeKatClient, ForeKatClientError


def _config() -> dict:
    return {
        "foreman_api_url": "https://forekat.example/api",
        "katello_api_url": "https://forekat.example/katello/api",
        "username": "foreman-user",
        "personal_access_token": "secret-token",
        "verify_ssl": True,
        "ca_bundle": None,
        "timeout_seconds": 30,
        "host_search": "",
    }


def test_get_paginated_falls_back_from_per_page_all(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())

    requests_mock.get(
        "https://forekat.example/api/hosts",
        [
            {"status_code": 400, "json": {"error": "unsupported per_page"}},
            {
                "status_code": 200,
                "json": {
                    "results": [{"id": 1, "name": "host01.example.com"}],
                    "subtotal": 2,
                    "total": 2,
                    "page": 1,
                    "per_page": 100,
                },
            },
            {
                "status_code": 200,
                "json": {
                    "results": [{"id": 2, "name": "host02.example.com"}],
                    "subtotal": 2,
                    "total": 2,
                    "page": 2,
                    "per_page": 100,
                },
            },
        ],
    )

    result = client.get_paginated(client.config["foreman_api_url"], "/hosts")

    assert result.mode == "numeric"
    assert [item["id"] for item in result.items] == [1, 2]
    assert len(result.metadata) == 2


def test_get_paginated_uses_per_page_all_when_supported(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())

    requests_mock.get(
        "https://forekat.example/api/hosts",
        json={
            "results": [{"id": 1, "name": "host01.example.com"}],
            "subtotal": 1,
            "total": 1,
            "page": 1,
            "per_page": "all",
        },
    )

    result = client.get_paginated(client.config["foreman_api_url"], "/hosts")

    assert result.mode == "all"
    assert [item["id"] for item in result.items] == [1]
    assert requests_mock.request_history[0].qs["per_page"] == ["all"]


def test_get_paginated_falls_back_when_per_page_all_returns_partial_payload(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())

    requests_mock.get(
        "https://forekat.example/katello/api/host_collections",
        [
            {
                "status_code": 200,
                "json": {
                    "results": [],
                    "subtotal": 2,
                    "total": 2,
                    "page": 1,
                    "per_page": "all",
                },
            },
            {
                "status_code": 200,
                "json": {
                    "results": [
                        {"id": 10, "name": "Production"},
                        {"id": 11, "name": "Non-Production"},
                    ],
                    "subtotal": 2,
                    "total": 2,
                    "page": 1,
                    "per_page": 100,
                },
            },
        ],
    )

    result = client.get_paginated(client.config["katello_api_url"], "/host_collections")

    assert result.mode == "numeric"
    assert [item["name"] for item in result.items] == ["Production", "Non-Production"]
    assert [request.qs["per_page"][0] for request in requests_mock.request_history] == ["all", "100"]


def test_get_paginated_steps_down_through_numeric_page_sizes_on_timeout(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())

    requests_mock.get(
        "https://forekat.example/api/hosts",
        [
            {"exc": requests.exceptions.Timeout},
            {"exc": requests.exceptions.Timeout},
            {
                "status_code": 200,
                "json": {
                    "results": [{"id": 1, "name": "host01.example.com"}],
                    "subtotal": 2,
                    "total": 2,
                    "page": 1,
                    "per_page": 50,
                },
            },
            {
                "status_code": 200,
                "json": {
                    "results": [{"id": 2, "name": "host02.example.com"}],
                    "subtotal": 2,
                    "total": 2,
                    "page": 2,
                    "per_page": 50,
                },
            },
        ],
    )

    result = client.get_paginated(client.config["foreman_api_url"], "/hosts")

    assert result.mode == "numeric"
    assert [item["id"] for item in result.items] == [1, 2]
    assert [request.qs["per_page"][0] for request in requests_mock.request_history] == [
        "all",
        "100",
        "50",
        "50",
    ]


@pytest.mark.parametrize(
    ("status_code", "message_fragment"),
    [
        (401, "401 Unauthorized"),
        (403, "403 Forbidden"),
        (404, "404 Not Found"),
    ],
)
def test_request_json_reports_http_errors(requests_mock, status_code, message_fragment):
    client = ForeKatClient(_config(), session=requests.Session())
    requests_mock.get("https://forekat.example/api/hosts", status_code=status_code, json={"error": "nope"})

    with pytest.raises(ForeKatClientError, match=message_fragment):
        client._request_json("GET", "https://forekat.example/api/hosts")


def test_request_json_reports_invalid_json(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())
    requests_mock.get("https://forekat.example/api/hosts", text="not json", status_code=200)

    with pytest.raises(ForeKatClientError, match="invalid JSON"):
        client._request_json("GET", "https://forekat.example/api/hosts")


def test_client_configures_basic_auth_and_json_headers():
    client = ForeKatClient(_config(), session=requests.Session())

    assert client.session.headers["Accept"] == "application/json"
    assert client.session.headers["Content-Type"] == "application/json"
    assert client.session.auth.username == "foreman-user"
    assert client.session.auth.password == "secret-token"


def test_fetch_all_hosts_normalizes_and_warns_on_unusable_entries(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())
    requests_mock.get(
        "https://forekat.example/api/hosts",
        json={
            "results": [
                {"id": 1, "name": "HOST01.EXAMPLE.COM", "display_name": "host01.example.com"},
                {"id": 2, "display_name": "host02.example.com"},
                {"id": 3, "interfaces": [{"fqdn": "host03.example.com"}]},
                {"id": 4, "name": "notfqdn"},
            ],
            "subtotal": 4,
            "total": 4,
            "page": 1,
            "per_page": "all",
        },
    )

    result = client.fetch_all_hosts()

    assert [host["fqdn"] for host in result["hosts"]] == [
        "host01.example.com",
        "host02.example.com",
        "host03.example.com",
    ]
    assert any("Skipped host entry without a usable FQDN" in warning for warning in result["warnings"])


def test_fetch_all_hosts_uses_display_name_and_interfaces(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())
    requests_mock.get(
        "https://forekat.example/api/hosts",
        json={
            "results": [
                {"id": 1, "display_name": "HOST01.EXAMPLE.COM"},
                {"id": 2, "interfaces": [{"fqdn": "host02.example.com"}]},
            ],
            "subtotal": 2,
            "total": 2,
            "page": 1,
            "per_page": "all",
        },
    )

    result = client.fetch_all_hosts()

    assert [host["fqdn"] for host in result["hosts"]] == ["host01.example.com", "host02.example.com"]


def test_fetch_host_collections_extracts_members_from_multiple_shapes(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())
    requests_mock.get(
        "https://forekat.example/katello/api/host_collections",
        json={
            "results": [
                {"id": 10, "name": "Production"},
                {"id": 11, "name": "Non-Production"},
            ],
            "subtotal": 2,
            "total": 2,
            "page": 1,
            "per_page": "all",
        },
    )
    requests_mock.get(
        "https://forekat.example/katello/api/host_collections/10",
        json={
            "id": 10,
            "name": "Production",
            "host_ids": [1, 2],
            "hosts": [
                {"id": 1, "fqdn": "host01.example.com"},
                {"id": 2, "display_name": "host02.example.com"},
            ],
        },
    )
    requests_mock.get(
        "https://forekat.example/katello/api/host_collections/11",
        json={
            "id": 11,
            "name": "Non-Production",
            "members": [
                {"host": {"id": 3, "name": "host03.example.com"}},
            ],
        },
    )

    result = client.fetch_host_collections()

    assert [collection["name"] for collection in result["collections"]] == [
        "Production",
        "Non-Production",
    ]
    assert result["collections"][0]["host_ids"] == [1, 2]
    assert result["collections"][0]["host_fqdns"] == [
        "host01.example.com",
        "host02.example.com",
    ]
    assert result["collections"][1]["host_fqdns"] == ["host03.example.com"]


def test_fetch_host_collection_index_uses_katello_api_url(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())
    requests_mock.get(
        "https://forekat.example/katello/api/host_collections",
        json={
            "results": [{"id": 10, "name": "Production"}],
            "subtotal": 1,
            "total": 1,
            "page": 1,
            "per_page": "all",
        },
    )

    result = client.fetch_host_collection_index()

    assert result["collections"] == [{"id": 10, "name": "Production"}]
    assert requests_mock.request_history[0].url.startswith(
        "https://forekat.example/katello/api/host_collections"
    )


def test_fetch_host_collection_detail_extracts_members(requests_mock):
    client = ForeKatClient(_config(), session=requests.Session())
    requests_mock.get(
        "https://forekat.example/katello/api/host_collections/10",
        json={
            "id": 10,
            "name": "Production",
            "host_ids": [1],
            "hosts": [{"id": 1, "name": "host01.example.com"}],
        },
    )

    result = client.fetch_host_collection_detail(10)

    assert result["collection"]["name"] == "Production"
    assert result["collection"]["host_ids"] == [1]
    assert result["collection"]["host_fqdns"] == ["host01.example.com"]


def test_forekat_client_rejects_placeholder_username():
    config = _config()
    config["username"] = "TODO_FOREMAN_USERNAME"

    with pytest.raises(ForeKatClientError, match="ForeKat API username is not configured"):
        ForeKatClient(config)
