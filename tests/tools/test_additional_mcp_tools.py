from __future__ import annotations

from dataclasses import dataclass

from spice_mcp.core.models import TableColumn, TableDescription, TableSummary
from spice_mcp.mcp import server
from spice_mcp.mcp.tools.sui_package_overview import SuiPackageOverviewTool


@dataclass
class StubDiscovery:
    schemas: list[str]
    tables: list[str]
    description: TableDescription

    def find_schemas(self, keyword: str) -> list[str]:
        assert keyword == "eth"
        return list(self.schemas)

    def list_tables(self, schema: str, limit: int | None = None):
        assert schema == "foo"
        summaries = [TableSummary(schema="foo", table=t) for t in self.tables]
        if limit is not None:
            return summaries[:limit]
        return summaries

    def describe_table(self, schema: str, table: str) -> TableDescription:
        assert schema == "s"
        assert table == "t"
        return self.description


class StubSuiService:
    def package_overview(self, packages, *, hours: int, timeout_seconds: float | None):
        return {"ok": True, "count": len(packages), "hours": hours, "timeout_seconds": timeout_seconds}


def test_find_tables_tool(monkeypatch):
    monkeypatch.setenv("DUNE_API_KEY", "k")
    stub = StubDiscovery(
        schemas=["foo", "bar"],
        tables=["t1", "t2"],
        description=TableDescription("s.t", []),
    )
    monkeypatch.setattr(server, "_ensure_initialized", lambda: None)
    server.DISCOVERY_SERVICE = stub  # type: ignore[assignment]

    out = server._dune_find_tables_impl(keyword="eth", schema="foo", limit=10)
    assert out.get("schemas") == ["foo", "bar"]
    assert out.get("tables") == ["t1", "t2"]


def test_describe_table_tool(monkeypatch):
    monkeypatch.setenv("DUNE_API_KEY", "k")
    desc = TableDescription(
        "s.t",
        columns=[
            TableColumn(name="a", dune_type="VARCHAR", polars_dtype="Utf8"),
            TableColumn(name="b", dune_type="INT", polars_dtype="Int64"),
        ],
    )
    stub = StubDiscovery(schemas=[], tables=[], description=desc)
    monkeypatch.setattr(server, "_ensure_initialized", lambda: None)
    server.DISCOVERY_SERVICE = stub  # type: ignore[assignment]

    out = server._dune_describe_table_impl(schema="s", table="t")
    assert out["columns"][0]["name"] == "a"
    assert out["columns"][1]["dune_type"] == "INT"


def test_sui_package_overview_tool(monkeypatch):
    tool = SuiPackageOverviewTool(StubSuiService())
    out = tool.execute(packages=["0x1", "0x2"], hours=12, timeout_seconds=5)
    assert out["ok"] is True
    assert out["count"] == 2
    assert out["hours"] == 12


