"""
Tests for unified dune_discover tool.
"""
from __future__ import annotations

from dataclasses import dataclass

from spice_mcp.core.models import SchemaMatch, TableColumn, TableDescription, TableSummary
from spice_mcp.mcp import server


class StubDuneExplorer:
    """Stub explorer for Dune API discovery (returns SchemaMatch objects)."""
    schemas: list[str]
    tables: list[str]
    description: TableDescription

    def __init__(self):
        self.schemas = ["sui_base"]
        self.tables = ["events", "transactions"]
        self.description = TableDescription("sui_base.events", [])

    def find_schemas(self, keyword: str):
        if keyword == "sui":
            return [SchemaMatch(schema=s) for s in self.schemas]
        return []

    def list_tables(self, schema: str, limit: int | None = None):
        if schema == "sui_base":
            summaries = [TableSummary(schema=schema, table=t) for t in self.tables]
            if limit:
                return summaries[:limit]
            return summaries
        return []

    def describe_table(self, schema: str, table: str):
        return self.description


class StubSpellbookExplorer:
    """Stub for Spellbook explorer."""
    def __init__(self):
        # Mock models cache structure matching real SpellbookExplorer
        self._models_cache = {
            "daily_spellbook": [
                {
                    "name": "layerzero_send",
                    "schema": "daily_spellbook",
                    "dune_schema": "layerzero",
                    "dune_alias": "send",
                    "dune_table": "layerzero.send",
                },
                {
                    "name": "layerzero_chain_list",
                    "schema": "daily_spellbook",
                    "dune_schema": "layerzero",
                    "dune_alias": "chain_list",
                    "dune_table": "layerzero.chain_list",
                },
            ]
        }

    def find_schemas(self, keyword: str):
        if "layerzero" in keyword.lower():
            return [SchemaMatch(schema="daily_spellbook")]
        return []

    def list_tables(self, schema: str, limit: int | None = None):
        if schema == "daily_spellbook":
            tables = ["layerzero_send", "layerzero_chain_list"]
            summaries = [TableSummary(schema=schema, table=t) for t in tables]
            if limit:
                return summaries[:limit]
            return summaries
        return []

    def describe_table(self, schema: str, table: str):
        if schema == "daily_spellbook" and table == "layerzero_send":
            return TableDescription(
                "daily_spellbook.layerzero_send",
                columns=[
                    TableColumn(name="block_time", dune_type="TIMESTAMP"),
                    TableColumn(name="tx_hash", dune_type="VARCHAR"),
                ],
            )
        raise ValueError(f"Table {schema}.{table} not found")
    
    def _load_models(self):
        """Return mock models cache matching real SpellbookExplorer structure."""
        return self._models_cache


class StubVerificationService:
    """Stub verification service that always returns True (all tables verified)."""
    def verify_tables_batch(self, tables):
        """Return True for all tables."""
        return {f"{schema}.{table}": True for schema, table in tables}


def test_unified_discover_spellbook_only(monkeypatch, tmp_path):
    """Test unified discover with spellbook source only."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    server._ensure_initialized()
    server.SPELLBOOK_EXPLORER = StubSpellbookExplorer()
    server.VERIFICATION_SERVICE = StubVerificationService()
    
    result = server._unified_discover_impl(keyword="layerzero", source="spellbook", include_columns=False)
    
    assert result["source"] == "spellbook"
    assert "daily_spellbook" in result["schemas"]
    assert len(result["tables"]) > 0
    assert all(t["source"] == "spellbook" for t in result["tables"])
    assert all("fully_qualified_name" in t for t in result["tables"])


def test_unified_discover_dune_only(monkeypatch, tmp_path):
    """Test unified discover with dune source only."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    server._ensure_initialized()
    stub_explorer = StubDuneExplorer()
    # Replace the explorer on the discovery service
    from spice_mcp.service_layer.discovery_service import DiscoveryService
    server.DISCOVERY_SERVICE = DiscoveryService(stub_explorer)
    
    result = server._unified_discover_impl(keyword="sui", source="dune")
    
    assert result["source"] == "dune"
    assert "sui_base" in result["schemas"]
    assert len(result["tables"]) == 0  # No schema specified, so no tables listed


def test_unified_discover_both_sources(monkeypatch, tmp_path):
    """Test unified discover with both sources."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    server._ensure_initialized()
    server.SPELLBOOK_EXPLORER = StubSpellbookExplorer()
    server.VERIFICATION_SERVICE = StubVerificationService()
    stub_explorer = StubDuneExplorer()
    from spice_mcp.service_layer.discovery_service import DiscoveryService
    server.DISCOVERY_SERVICE = DiscoveryService(stub_explorer)
    
    result = server._unified_discover_impl(keyword="layerzero", source="both", include_columns=False)
    
    assert result["source"] == "both"
    assert len(result["schemas"]) > 0
    assert len(result["tables"]) > 0
    # Should have spellbook tables
    spellbook_tables = [t for t in result["tables"] if t["source"] == "spellbook"]
    assert len(spellbook_tables) > 0


def test_unified_discover_multiple_keywords(monkeypatch, tmp_path):
    """Test unified discover with multiple keywords."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    server._ensure_initialized()
    server.SPELLBOOK_EXPLORER = StubSpellbookExplorer()
    server.VERIFICATION_SERVICE = StubVerificationService()
    
    result = server._unified_discover_impl(keyword=["layerzero", "bridge"], source="spellbook", include_columns=False)
    
    assert len(result["tables"]) > 0
    # Should find models matching either keyword
    table_names = [t["table"] for t in result["tables"]]
    assert any("layerzero" in name.lower() for name in table_names) or any("bridge" in name.lower() for name in table_names)


def test_unified_discover_with_schema(monkeypatch, tmp_path):
    """Test unified discover with schema specified."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    server._ensure_initialized()
    server.SPELLBOOK_EXPLORER = StubSpellbookExplorer()
    server.VERIFICATION_SERVICE = StubVerificationService()
    
    result = server._unified_discover_impl(schema="daily_spellbook", source="spellbook", limit=10, include_columns=True)
    
    assert len(result["tables"]) > 0
    assert all(t["schema"] == "daily_spellbook" for t in result["tables"])
    # With include_columns=True, should have columns
    if result["tables"]:
        first_table = result["tables"][0]
        assert "columns" in first_table


def test_unified_discover_response_format(monkeypatch, tmp_path):
    """Test that unified discover returns consistent format."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    server._ensure_initialized()
    server.SPELLBOOK_EXPLORER = StubSpellbookExplorer()
    server.VERIFICATION_SERVICE = StubVerificationService()
    
    result = server._unified_discover_impl(keyword="layerzero", source="spellbook")
    
    # Verify response structure
    assert "schemas" in result
    assert "tables" in result
    assert "source" in result
    assert isinstance(result["schemas"], list)
    assert isinstance(result["tables"], list)
    
    # Verify table structure
    if result["tables"]:
        table = result["tables"][0]
        assert "schema" in table
        assert "table" in table
        assert "fully_qualified_name" in table
        assert "source" in table
        assert table["source"] in ("dune", "spellbook")
        
        # Verify new fields for Spellbook models
        if table["source"] == "spellbook":
            assert "dune_schema" in table
            assert "dune_alias" in table
            assert "dune_table" in table
            assert "verified" in table
            assert table["verified"] is True

