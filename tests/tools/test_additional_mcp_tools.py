from __future__ import annotations

from dataclasses import dataclass

from spice_mcp.core.models import TableColumn, TableDescription, TableSummary
from spice_mcp.mcp import server


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


def test_discover_tool_dune_only(monkeypatch):
    """Test dune_discover with source='dune'."""
    monkeypatch.setenv("DUNE_API_KEY", "k")
    stub = StubDiscovery(
        schemas=["foo", "bar"],
        tables=["t1", "t2"],
        description=TableDescription("s.t", []),
    )
    monkeypatch.setattr(server, "_ensure_initialized", lambda: None)
    server.DISCOVERY_SERVICE = stub  # type: ignore[assignment]

    out = server._unified_discover_impl(keyword="eth", schema="foo", limit=10, source="dune")
    assert "foo" in out.get("schemas", []) or "bar" in out.get("schemas", [])
    assert len(out.get("tables", [])) > 0
    if out.get("tables"):
        assert out["tables"][0]["schema"] == "foo"


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


def test_spellbook_schema_discovery(monkeypatch):
    """Test discovery tools work with spellbook schema."""
    monkeypatch.setenv("DUNE_API_KEY", "k")
    
    # Create a flexible stub for spellbook testing
    class SpellbookStubDiscovery:
        def find_schemas(self, keyword: str) -> list[str]:
            if "spellbook" in keyword.lower():
                return ["spellbook", "spellbook_ethereum"]
            return []
        
        def list_tables(self, schema: str, limit: int | None = None):
            if schema == "spellbook":
                tables = ["erc20_transfers", "dex_trades", "nft_transfers"]
                summaries = [TableSummary(schema="spellbook", table=t) for t in tables]
                if limit is not None:
                    return summaries[:limit]
                return summaries
            return []
        
        def describe_table(self, schema: str, table: str) -> TableDescription:
            if schema == "spellbook" and table == "erc20_transfers":
                return TableDescription(
                    "spellbook.erc20_transfers",
                    columns=[
                        TableColumn(name="block_time", dune_type="TIMESTAMP", polars_dtype="Datetime"),
                        TableColumn(name="token_address", dune_type="VARCHAR", polars_dtype="Utf8"),
                        TableColumn(name="amount", dune_type="DECIMAL", polars_dtype="Float64"),
                    ],
                )
            raise ValueError(f"Table {schema}.{table} not found")
    
    stub = SpellbookStubDiscovery()
    monkeypatch.setattr(server, "_ensure_initialized", lambda: None)
    server.DISCOVERY_SERVICE = stub  # type: ignore[assignment]
    
    # Test finding spellbook schemas using dune_discover
    out = server._unified_discover_impl(keyword="spellbook", source="dune")
    assert "spellbook" in out.get("schemas", []) or "spellbook_ethereum" in out.get("schemas", [])
    
    # Test listing tables in spellbook schema using dune_discover
    out = server._unified_discover_impl(schema="spellbook", limit=10, source="dune")
    table_names = [t["table"] for t in out.get("tables", [])]
    assert "erc20_transfers" in table_names
    
    # Test describing a spellbook table
    out = server._dune_describe_table_impl(schema="spellbook", table="erc20_transfers")
    assert out["table"] == "spellbook.erc20_transfers"
    assert len(out["columns"]) == 3
    assert out["columns"][0]["name"] == "block_time"
    assert out["columns"][1]["name"] == "token_address"
    assert out["columns"][2]["name"] == "amount"


