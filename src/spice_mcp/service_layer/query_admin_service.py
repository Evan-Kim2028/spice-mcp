from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..core.ports import QueryAdmin


class QueryAdminService:
    """Service for saved query management (create/update/fork)."""

    def __init__(self, admin: QueryAdmin):
        self.admin = admin

    def get(self, query_id: int) -> Mapping[str, Any]:
        return self.admin.get(query_id)

    def create(self, *, name: str, query_sql: str, description: str | None = None, tags: Sequence[str] | None = None, parameters: Sequence[Mapping[str, Any]] | None = None) -> Mapping[str, Any]:
        return self.admin.create(name=name, query_sql=query_sql, description=description, tags=list(tags) if tags else None, parameters=list(parameters) if parameters else None)

    def update(self, query_id: int, *, name: str | None = None, query_sql: str | None = None, description: str | None = None, tags: Sequence[str] | None = None, parameters: Sequence[Mapping[str, Any]] | None = None) -> Mapping[str, Any]:
        return self.admin.update(query_id, name=name, query_sql=query_sql, description=description, tags=list(tags) if tags else None, parameters=list(parameters) if parameters else None)

    def fork(self, source_query_id: int, *, name: str | None = None) -> Mapping[str, Any]:
        return self.admin.fork(source_query_id, name=name)

    def archive(self, query_id: int) -> Mapping[str, Any]:
        return self.admin.archive(query_id)

    def unarchive(self, query_id: int) -> Mapping[str, Any]:
        return self.admin.unarchive(query_id)

