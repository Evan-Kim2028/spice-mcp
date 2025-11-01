from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from .models import (
    QueryRequest,
    QueryResult,
    ResultMetadata,
    SchemaMatch,
    TableDescription,
    TableSummary,
)


class QueryExecutor(Protocol):
    """Port for executing Dune queries."""

    def execute(self, request: QueryRequest) -> QueryResult:
        ...

    def fetch_metadata(
        self, request: QueryRequest, *, execution: Mapping[str, Any] | None = None
    ) -> ResultMetadata:
        ...


class CatalogExplorer(Protocol):
    """Port for schema/table discovery operations."""

    def find_schemas(self, keyword: str) -> Sequence[SchemaMatch]:
        ...

    def list_tables(self, schema: str, limit: int | None = None) -> Sequence[TableSummary]:
        ...

    def describe_table(self, schema: str, table: str) -> TableDescription:
        ...


class QueryAdmin(Protocol):
    """Port for managing Dune saved queries."""

    def get(self, query_id: int) -> Mapping[str, Any]:
        ...

    def create(self, *, name: str, query_sql: str, description: str | None = None, tags: Sequence[str] | None = None, parameters: Sequence[Mapping[str, Any]] | None = None) -> Mapping[str, Any]:
        ...

    def update(self, query_id: int, *, name: str | None = None, query_sql: str | None = None, description: str | None = None, tags: Sequence[str] | None = None, parameters: Sequence[Mapping[str, Any]] | None = None) -> Mapping[str, Any]:
        ...

    def fork(self, source_query_id: int, *, name: str | None = None) -> Mapping[str, Any]:
        ...
