from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..http_client import HttpClient, HttpClientConfig
from . import urls


class DuneAdminAdapter:
    """Lightweight client for Dune saved query management."""

    def __init__(
        self,
        api_key: str,
        *,
        http_client: HttpClient | None = None,
        http_config: HttpClientConfig | None = None,
    ):
        self.api_key = api_key
        config = http_config or HttpClientConfig()
        self._http = http_client or HttpClient(config)

    def _headers(self) -> Mapping[str, str]:
        return {
            "X-Dune-API-Key": self.api_key,
            "User-Agent": "spice-mcp-admin/1",
            "Content-Type": "application/json",
        }

    def get(self, query_id: int) -> dict[str, Any]:
        url = urls.url_templates["query"].format(query_id=query_id)
        resp = self._http.request("GET", url, headers=self._headers())
        return resp.json()

    def create(
        self,
        *,
        name: str,
        query_sql: str,
        description: str | None = None,
        tags: list[str] | None = None,
        parameters: list[dict] | None = None,
        is_private: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "query_sql": query_sql, "is_private": is_private}
        if description:
            body["description"] = description
        # Auto-attach 'spice-mcp' tag if tags not provided
        if tags is None:
            body["tags"] = ["spice-mcp"]
        else:
            body["tags"] = tags
        if parameters is not None:
            body["parameters"] = parameters
        resp = self._http.request(
            "POST",
            urls.url_templates["query_create"],
            headers=self._headers(),
            json=body,
            timeout=20,
        )
        return resp.json()

    def update(self, query_id: int, *, name: str | None = None, query_sql: str | None = None, description: str | None = None, tags: list[str] | None = None, parameters: list[dict] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if query_sql is not None:
            body["query_sql"] = query_sql
        if description is not None:
            body["description"] = description
        if tags is not None:
            body["tags"] = tags
        if parameters is not None:
            body["parameters"] = parameters
        url = urls.url_templates["query"].format(query_id=query_id)
        resp = self._http.request(
            "PATCH",
            url,
            headers=self._headers(),
            json=body,
            timeout=20,
        )
        return resp.json()

    def fork(self, source_query_id: int, *, name: str | None = None) -> dict[str, Any]:
        url = urls.url_templates.get("query_fork", f"https://api.dune.com/api/v1/query/{source_query_id}/fork").format(query_id=source_query_id)
        body: dict[str, Any] = {"name": name} if name else {}
        resp = self._http.request(
            "POST",
            url,
            headers=self._headers(),
            json=body,
            timeout=20,
        )
        return resp.json()

    def archive(self, query_id: int) -> dict[str, Any]:
        """Archive a saved query."""
        url = urls.url_templates["query_archive"].format(query_id=query_id)
        resp = self._http.request(
            "POST",
            url,
            headers=self._headers(),
            timeout=20,
        )
        return resp.json()

    def unarchive(self, query_id: int) -> dict[str, Any]:
        """Unarchive a saved query."""
        url = urls.url_templates["query_unarchive"].format(query_id=query_id)
        resp = self._http.request(
            "POST",
            url,
            headers=self._headers(),
            timeout=20,
        )
        return resp.json()
