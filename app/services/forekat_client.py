from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from requests import Response
from requests.auth import HTTPBasicAuth


class ForeKatClientError(RuntimeError):
    pass


@dataclass(slots=True)
class PaginatedResult:
    items: list[dict[str, Any]]
    metadata: list[dict[str, Any]]
    mode: str


class ForeKatClient:
    def __init__(self, config: dict[str, Any], session: requests.Session | None = None):
        username = str(config.get("username", "")).strip()
        if username == "TODO_FOREMAN_USERNAME" or not username:
            raise ForeKatClientError(
                "ForeKat API username is not configured. Set forekat.username in config.yaml before making API calls."
            )

        token = str(config.get("personal_access_token", "")).strip()
        if not token:
            raise ForeKatClientError(
                "ForeKat personal access token is not configured in config.yaml."
            )

        self.config = config
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self.session.auth = HTTPBasicAuth(username, token)
        self.timeout = int(config.get("timeout_seconds", 30))
        self.verify = config.get("ca_bundle") or bool(config.get("verify_ssl", True))

    def get_paginated(
        self,
        base_url: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> PaginatedResult:
        normalized_params = dict(params or {})
        try:
            response = self._request_json(
                "GET",
                self._build_url(base_url, path),
                params={**normalized_params, "page": 1, "per_page": "all"},
                timeout_override=min(self.timeout, 5),
            )
            items, metadata = self._extract_paginated_items(response)
            if self._is_incomplete_all_result(metadata):
                raise ForeKatClientError(
                    "ForeKat per_page=all returned fewer results than the response metadata reported."
                )
            return PaginatedResult(items=items, metadata=[metadata], mode="all")
        except ForeKatClientError as exc:
            if not self._supports_fallback(exc):
                raise

        last_error: ForeKatClientError | None = None
        for per_page in (100, 50, 20, 10):
            try:
                return self._paginate_numeric(base_url, path, normalized_params, per_page)
            except ForeKatClientError as exc:
                last_error = exc
                if not self._supports_page_size_fallback(exc):
                    raise

        if last_error is not None:
            raise last_error
        raise ForeKatClientError(f"Unable to paginate ForeKat results for {self._build_url(base_url, path)}.")

    def fetch_all_hosts(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        host_search = str(self.config.get("host_search", "")).strip()
        if host_search:
            params["search"] = host_search

        result = self.get_paginated(self.config["foreman_api_url"], "/hosts", params=params)
        normalized_hosts: list[dict[str, Any]] = []
        warnings: list[str] = []
        seen_fqdns: set[str] = set()

        for host in result.items:
            fqdn = self._extract_host_fqdn(host)
            if not fqdn:
                warnings.append(
                    f"Skipped host entry without a usable FQDN for Foreman host id {host.get('id', 'unknown')}."
                )
                continue
            if fqdn in seen_fqdns:
                warnings.append(f"Skipped duplicate host FQDN {fqdn}.")
                continue
            seen_fqdns.add(fqdn)
            normalized_hosts.append(
                {
                    "id": host.get("id"),
                    "fqdn": fqdn,
                    "name": host.get("name"),
                    "display_name": host.get("display_name"),
                    "raw": host,
                }
            )

        return {
            "hosts": normalized_hosts,
            "warnings": warnings,
            "metadata": result.metadata,
        }

    def fetch_hosts(self) -> list[str]:
        return [host["fqdn"] for host in self.fetch_all_hosts()["hosts"]]

    def fetch_host_collection_index(self) -> dict[str, Any]:
        result = self.get_paginated(self.config["katello_api_url"], "/host_collections")
        return {
            "collections": result.items,
            "warnings": [],
            "metadata": result.metadata,
        }

    def fetch_host_collection_detail(self, collection_id: Any) -> dict[str, Any]:
        detail = self._request_json(
            "GET",
            self._build_url(self.config["katello_api_url"], f"/host_collections/{collection_id}"),
        )
        host_ids, host_fqdns, warnings = self._extract_host_collection_members(detail)
        return {
            "collection": {
                "id": detail.get("id", collection_id),
                "name": str(detail.get("name") or "").strip(),
                "host_ids": host_ids,
                "host_fqdns": host_fqdns,
                "raw": detail,
            },
            "warnings": warnings,
        }

    def fetch_host_collections(self) -> dict[str, Any]:
        index_result = self.fetch_host_collection_index()
        collections: list[dict[str, Any]] = []
        warnings: list[str] = list(index_result["warnings"])
        for collection in index_result["collections"]:
            collection_id = collection.get("id")
            if collection_id is None:
                warnings.append("Skipped a Katello host collection without an id.")
                continue
            detail_result = self.fetch_host_collection_detail(collection_id)
            warnings.extend(detail_result["warnings"])
            detailed_collection = detail_result["collection"]
            if not detailed_collection["name"]:
                detailed_collection["name"] = str(collection.get("name") or "").strip()
            collections.append(detailed_collection)
        return {
            "collection_index": index_result["collections"],
            "collections": collections,
            "warnings": warnings,
            "metadata": index_result["metadata"],
        }

    def check_status(self) -> dict[str, Any]:
        return self._request_json(
            "GET",
            self._build_url(self.config["foreman_api_url"], "/status"),
        )

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        timeout_override: int | None = None,
    ) -> dict[str, Any]:
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                timeout=timeout_override or self.timeout,
                verify=self.verify,
            )
        except requests.exceptions.SSLError as exc:
            raise ForeKatClientError(
                f"TLS verification failed while calling {url}."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ForeKatClientError(
                f"Connection to ForeKat failed while calling {url}."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ForeKatClientError(
                f"Request to ForeKat timed out after {self.timeout} seconds for {url}."
            ) from exc
        except requests.RequestException as exc:
            raise ForeKatClientError(f"Request to ForeKat failed for {url}.") from exc

        self._raise_for_status(response, url)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ForeKatClientError(
                f"ForeKat returned invalid JSON for {url}."
            ) from exc
        if not isinstance(payload, dict):
            raise ForeKatClientError(
                f"ForeKat returned an unexpected JSON structure for {url}."
            )
        return payload

    def _raise_for_status(self, response: Response, url: str) -> None:
        if response.status_code == 401:
            raise ForeKatClientError(f"ForeKat authentication failed for {url} (401 Unauthorized).")
        if response.status_code == 403:
            raise ForeKatClientError(f"ForeKat access was denied for {url} (403 Forbidden).")
        if response.status_code == 404:
            raise ForeKatClientError(f"ForeKat endpoint not found for {url} (404 Not Found).")
        if response.status_code >= 400:
            raise ForeKatClientError(
                f"ForeKat request failed for {url} with HTTP {response.status_code}."
            )

    def _extract_paginated_items(self, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        items = payload.get("results")
        if not isinstance(items, list):
            raise ForeKatClientError("ForeKat response did not contain a 'results' list.")
        metadata = {
            "total": payload.get("total"),
            "subtotal": payload.get("subtotal"),
            "page": payload.get("page"),
            "per_page": payload.get("per_page"),
            "returned": len(items),
        }
        return items, metadata

    def _extract_host_fqdn(self, host: dict[str, Any]) -> str | None:
        candidates = [
            host.get("name"),
            host.get("display_name"),
        ]
        interfaces = host.get("interfaces") or host.get("all_interfaces") or []
        if isinstance(interfaces, list):
            for interface in interfaces:
                if not isinstance(interface, dict):
                    continue
                for key in ("fqdn", "name"):
                    value = interface.get(key)
                    if value:
                        candidates.append(value)
        for candidate in candidates:
            normalized = self._normalize_fqdn(candidate)
            if normalized:
                return normalized
        return None

    def _extract_host_collection_members(self, payload: dict[str, Any]) -> tuple[list[int], list[str], list[str]]:
        host_ids: list[int] = []
        host_fqdns: list[str] = []
        warnings: list[str] = []
        seen_ids: set[int] = set()
        seen_fqdns: set[str] = set()

        def add_host_id(value: Any) -> None:
            host_id = self._coerce_int(value)
            if host_id is None or host_id in seen_ids:
                return
            seen_ids.add(host_id)
            host_ids.append(host_id)

        def add_host_fqdn(value: Any) -> None:
            fqdn = self._normalize_fqdn(value)
            if fqdn is None or fqdn in seen_fqdns:
                return
            seen_fqdns.add(fqdn)
            host_fqdns.append(fqdn)

        def visit(value: Any, host_context: bool = False) -> None:
            if isinstance(value, list):
                for item in value:
                    visit(item, host_context)
                return
            if not isinstance(value, dict):
                if host_context:
                    add_host_id(value)
                return

            if "host_ids" in value and isinstance(value["host_ids"], list):
                for item in value["host_ids"]:
                    add_host_id(item)

            for key in ("hosts", "results", "members", "content_hosts", "host_collection_hosts"):
                if key in value:
                    visit(value[key], True)

            if host_context or any(key in value for key in ("fqdn", "display_name")):
                add_host_id(value.get("id"))
                for key in ("fqdn", "display_name", "name"):
                    if key in value:
                        add_host_fqdn(value.get(key))

            for key in ("host", "record"):
                if key in value:
                    visit(value[key], True)

        visit(payload, False)

        if not host_ids and not host_fqdns:
            warnings.append(
                f"Host collection {payload.get('name', 'unknown')} did not expose any host membership details."
            )

        return host_ids, host_fqdns, warnings

    def _normalize_fqdn(self, value: Any) -> str | None:
        if not value:
            return None
        fqdn = str(value).strip().lower()
        return fqdn if "." in fqdn else None

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _build_url(self, base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    def _coerce_total(self, metadata: dict[str, Any]) -> int | None:
        for key in ("subtotal", "total"):
            value = metadata.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        return None

    def _is_incomplete_all_result(self, metadata: dict[str, Any]) -> bool:
        expected_total = self._coerce_total(metadata)
        returned = metadata.get("returned")
        if expected_total is None or not isinstance(returned, int):
            return False
        return returned < expected_total

    def _supports_fallback(self, exc: ForeKatClientError) -> bool:
        message = str(exc)
        return any(
            token in message
            for token in (
                "HTTP 400",
                "HTTP 404",
                "HTTP 422",
                "timed out",
                "Request to ForeKat failed",
                "Connection to ForeKat failed",
                "TLS verification failed",
                "per_page=all",
            )
        )

    def _supports_page_size_fallback(self, exc: ForeKatClientError) -> bool:
        message = str(exc)
        return any(
            token in message
            for token in (
                "timed out",
                "Request to ForeKat failed",
                "Connection to ForeKat failed",
                "TLS verification failed",
            )
        )

    def _paginate_numeric(
        self,
        base_url: str,
        path: str,
        params: dict[str, Any],
        per_page: int,
    ) -> PaginatedResult:
        page = 1
        items: list[dict[str, Any]] = []
        metadata: list[dict[str, Any]] = []
        expected_total: int | None = None
        url = self._build_url(base_url, path)

        while True:
            response = self._request_json(
                "GET",
                url,
                params={**params, "page": page, "per_page": per_page},
            )
            batch, page_meta = self._extract_paginated_items(response)
            metadata.append(page_meta)
            items.extend(batch)

            if expected_total is None:
                expected_total = self._coerce_total(page_meta)

            if not batch:
                break
            if expected_total is not None and len(items) >= expected_total:
                break
            if expected_total is None and len(batch) < per_page:
                break
            page += 1

        return PaginatedResult(items=items, metadata=metadata, mode="numeric")
