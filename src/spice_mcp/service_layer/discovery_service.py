from __future__ import annotations

from ..core.models import TableDescription, TableSummary
from ..core.ports import CatalogExplorer


class DiscoveryService:
    """High-level discovery helpers used by MCP tools."""

    def __init__(self, explorer: CatalogExplorer):
        self.explorer = explorer

    def find_schemas(self, keyword: str) -> list[str]:
        return [match.schema for match in self.explorer.find_schemas(keyword)]

    def list_tables(self, schema: str, limit: int | None = None) -> list[TableSummary]:
        return list(self.explorer.list_tables(schema, limit=limit))

    def describe_table(self, schema: str, table: str) -> TableDescription:
        return self.explorer.describe_table(schema, table)
