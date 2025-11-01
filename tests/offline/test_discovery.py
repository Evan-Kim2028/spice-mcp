from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from spice_mcp.core.models import (
    SchemaMatch,
    TableColumn,
    TableDescription,
    TableSummary,
)
from spice_mcp.service_layer.discovery_service import DiscoveryService


@dataclass
class StubExplorer:
    schemas: Sequence[SchemaMatch]
    tables: Sequence[TableSummary]
    description: TableDescription

    def find_schemas(self, keyword: str) -> Sequence[SchemaMatch]:
        assert keyword == "abc"
        return self.schemas

    def list_tables(self, schema: str, limit: int | None = None) -> Sequence[TableSummary]:
        assert schema == "myschema"
        if limit is not None:
            return self.tables[:limit]
        return self.tables

    def describe_table(self, schema: str, table: str) -> TableDescription:
        assert schema == "myschema"
        assert table == "mytable"
        return self.description


def test_find_schemas_returns_names():
    explorer = StubExplorer(
        schemas=[SchemaMatch("a"), SchemaMatch("b")],
        tables=[],
        description=TableDescription("myschema.mytable", []),
    )
    service = DiscoveryService(explorer)
    out = service.find_schemas("abc")
    assert out == ["a", "b"]


def test_list_tables_passthrough_and_limit():
    tables = [
        TableSummary(schema="myschema", table="t1"),
        TableSummary(schema="myschema", table="t2"),
        TableSummary(schema="myschema", table="t3"),
    ]
    explorer = StubExplorer(
        schemas=[],
        tables=tables,
        description=TableDescription("myschema.mytable", []),
    )
    service = DiscoveryService(explorer)
    out = service.list_tables("myschema", limit=2)
    assert len(out) == 2
    assert [t.table for t in out] == ["t1", "t2"]


def test_describe_table_returns_columns():
    columns = [
        TableColumn(name="col1", dune_type="INT"),
        TableColumn(name="col2", polars_dtype="Utf8", comment="desc"),
    ]
    explorer = StubExplorer(
        schemas=[],
        tables=[],
        description=TableDescription("myschema.mytable", columns=columns),
    )
    service = DiscoveryService(explorer)
    desc = service.describe_table("myschema", "mytable")
    assert desc.fully_qualified_name == "myschema.mytable"
    assert len(desc.columns) == 2
    assert desc.columns[0].name == "col1"
