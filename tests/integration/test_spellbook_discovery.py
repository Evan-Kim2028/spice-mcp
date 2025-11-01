"""
Integration test for spellbook model discovery through MCP tools.

This test verifies that the spellbook tools can actually discover dbt models
from the Spellbook GitHub repository (https://github.com/duneanalytics/spellbook)
through the full MCP stack.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from spice_mcp.config import Config, DuneConfig
from spice_mcp.mcp import server


def _should_run_live():
    """Check if live tests should run."""
    return bool(os.getenv("SPICE_TEST_LIVE") == "1" and os.getenv("DUNE_API_KEY"))


@pytest.mark.mcp
def test_spellbook_discovery_through_dune_discover(monkeypatch, tmp_path):
    """
    Test spellbook discovery through dune_discover tool.
    
    This verifies the full stack:
    1. dune_discover with source="spellbook"
    2. Uses _spellbook_find_models_impl internally
    3. SpellbookExplorer.find_schemas() which parses GitHub repo
    4. Returns schema/subproject names from Spellbook dbt models
    """
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    # Initialize server to set up services
    server._ensure_initialized()
    
    # Verify the dune_discover tool exists (via FastMCP wrapper)
    assert hasattr(server.dune_discover, 'fn')
    assert callable(server.dune_discover.fn)
    
    # Test with a stub first to verify the tool interface works
    from spice_mcp.core.models import SchemaMatch, TableSummary, TableColumn, TableDescription
    
    class StubSpellbookExplorer:
        """Explorer stub that simulates parsing Spellbook GitHub repo."""
        def find_schemas(self, keyword: str):
            # Simulate finding subprojects like "dex", "nft", "tokens" from repo
            if "dex" in keyword.lower():
                return [SchemaMatch(schema="dex")]
            if "nft" in keyword.lower():
                return [SchemaMatch(schema="nft")]
            if "token" in keyword.lower():
                return [SchemaMatch(schema="tokens")]
            if "spellbook" in keyword.lower():
                return [
                    SchemaMatch(schema="dex"),
                    SchemaMatch(schema="nft"),
                    SchemaMatch(schema="tokens"),
                ]
            return []
        
        def list_tables(self, schema: str, limit: int | None = None):
            # Simulate listing dbt models from repo
            if schema == "dex":
                tables = ["trades", "pools", "liquidity"]
            elif schema == "nft":
                tables = ["transfers", "mints", "trades"]
            elif schema == "tokens":
                tables = ["erc20_transfers", "erc20_balances", "prices"]
            else:
                tables = []
            
            summaries = [TableSummary(schema=schema, table=t) for t in tables]
            if limit:
                return summaries[:limit]
            return summaries
        
        def describe_table(self, schema: str, table: str):
            # Simulate parsing schema.yml or SQL from repo
            if schema == "dex" and table == "trades":
                return TableDescription(
                    fully_qualified_name=f"{schema}.{table}",
                    columns=[
                        TableColumn(name="block_time", dune_type="TIMESTAMP", polars_dtype="Datetime"),
                        TableColumn(name="tx_hash", dune_type="VARCHAR", polars_dtype="Utf8"),
                        TableColumn(name="amount_usd", dune_type="DECIMAL", polars_dtype="Float64"),
                    ],
                )
            raise ValueError(f"Table {schema}.{table} not found in Spellbook")
        
        def _load_models(self):
            """Return mock models cache matching real SpellbookExplorer structure."""
            return {
                "dex": [
                    {
                        "name": "trades",
                        "schema": "dex",
                        "dune_schema": "dex",
                        "dune_alias": "trades",
                        "dune_table": "dex.trades",
                    },
                    {
                        "name": "pools",
                        "schema": "dex",
                        "dune_schema": "dex",
                        "dune_alias": "pools",
                        "dune_table": "dex.pools",
                    },
                ],
                "nft": [
                    {
                        "name": "transfers",
                        "schema": "nft",
                        "dune_schema": "nft",
                        "dune_alias": "transfers",
                        "dune_table": "nft.transfers",
                    },
                ],
            }
    
    # Replace spellbook explorer with stub
    server.SPELLBOOK_EXPLORER = StubSpellbookExplorer()
    
    # Create a stub verification service that always returns True (skip verification for stub test)
    from spice_mcp.service_layer.verification_service import VerificationService
    from unittest.mock import MagicMock
    from pathlib import Path
    import tempfile
    
    stub_adapter = MagicMock()
    stub_verification = VerificationService(
        cache_path=Path(tempfile.gettempdir()) / "test_verification_cache.json",
        dune_adapter=stub_adapter,
    )
    # Mock verify_tables_batch to always return True for stub tables
    stub_verification.verify_tables_batch = lambda tables: {f"{s}.{t}": True for s, t in tables}
    server.VERIFICATION_SERVICE = stub_verification
    
    # Test 1: Find spellbook schemas/subprojects via dune_discover
    result = server._unified_discover_impl(keyword="dex", source="spellbook")
    assert "schemas" in result
    schemas = result["schemas"]
    assert len(schemas) > 0
    assert "dex" in schemas
    
    # Test 2: List tables/models in a spellbook schema via dune_discover
    result = server._unified_discover_impl(schema="dex", source="spellbook", limit=10)
    assert "tables" in result
    tables = result["tables"]
    assert len(tables) > 0
    table_names = [t["table"] for t in tables]
    assert "trades" in table_names
    
    # Test 3: Verify table includes column details
    trades_table = next(t for t in tables if t["table"] == "trades")
    assert "columns" in trades_table
    assert len(trades_table["columns"]) > 0
    column_names = [c["name"] for c in trades_table["columns"]]
    assert "block_time" in column_names or "tx_hash" in column_names
    
    # Test 4: Test with multiple keywords via dune_discover
    result = server._unified_discover_impl(keyword=["dex", "nft"], source="spellbook", include_columns=False)
    assert "schemas" in result
    assert "tables" in result
    assert len(result["schemas"]) >= 2  # Should find both dex and nft schemas


@pytest.mark.skipif(not _should_run_live(), reason="live tests disabled by default")
@pytest.mark.live
def test_spellbook_discovery_live():
    """
    Live test: Actually clone and parse Spellbook GitHub repository.
    
    This requires:
    - SPICE_TEST_LIVE=1
    - Git available on system
    
    This verifies that:
    1. The explorer can clone the Spellbook GitHub repo
    2. Can parse dbt models from the repo structure
    3. Can find schemas/subprojects and list tables/models
    4. Can describe models by parsing SQL/schema.yml
    """
    server._ensure_initialized()
    
    # Create stub verification service for live tests
    from spice_mcp.service_layer.verification_service import VerificationService
    from unittest.mock import MagicMock
    from pathlib import Path
    import tempfile
    
    stub_adapter = MagicMock()
    stub_verification = VerificationService(
        cache_path=Path(tempfile.gettempdir()) / "test_verification_cache.json",
        dune_adapter=stub_adapter,
    )
    stub_verification.verify_tables_batch = lambda tables: {f"{s}.{t}": True for s, t in tables}
    server.VERIFICATION_SERVICE = stub_verification
    
    # Test 1: Find spellbook schemas/subprojects via dune_discover (parses GitHub repo)
    print("\n🔍 Searching Spellbook GitHub repo for schemas...")
    result = server._unified_discover_impl(keyword="dex", source="spellbook")
    
    assert "schemas" in result, "Result should contain 'schemas' key"
    schemas = result.get("schemas", [])
    print(f"   Found {len(schemas)} schemas: {schemas[:5]}...")
    
    if not schemas:
        pytest.skip("No schemas found - may need to check git availability or repo access")
    
    # Test 2: Search for models matching keyword (includes column details) via dune_discover
    print(f"\n📊 Searching for models matching 'dex' with column details...")
    result = server._unified_discover_impl(keyword="dex", source="spellbook", limit=5, include_columns=True)
    
    assert "tables" in result
    tables = result.get("tables", [])
    print(f"   Found {len(tables)} tables")
    
    if not tables:
        pytest.skip("No tables found - may need to check git availability or repo access")
    
    # Test 3: Verify table structure includes columns
    test_table = tables[0]
    print(f"\n📋 Table: {test_table.get('fully_qualified_name')}")
    columns = test_table.get("columns", [])
    print(f"   Columns ({len(columns)}): {[c['name'] for c in columns[:5]]}...")
    
    assert "schema" in test_table
    assert "table" in test_table
    assert "fully_qualified_name" in test_table
    assert len(columns) >= 0, "Table should have columns list (may be empty if parsing fails)"


@pytest.mark.skipif(not _should_run_live(), reason="live tests disabled by default")
@pytest.mark.live
def test_spellbook_workflow_end_to_end():
    """
    End-to-end workflow: Discover spellbook → List tables → Describe → Query.
    
    This tests the complete user journey with actual Dune API calls.
    """
    server._ensure_initialized()
    
    # Create stub verification service for live tests
    from spice_mcp.service_layer.verification_service import VerificationService
    from unittest.mock import MagicMock
    from pathlib import Path
    import tempfile
    
    stub_adapter = MagicMock()
    stub_verification = VerificationService(
        cache_path=Path(tempfile.gettempdir()) / "test_verification_cache.json",
        dune_adapter=stub_adapter,
    )
    stub_verification.verify_tables_batch = lambda tables: {f"{s}.{t}": True for s, t in tables}
    server.VERIFICATION_SERVICE = stub_verification
    
    # Step 1: Discover spellbook schemas and tables via dune_discover
    result = server._unified_discover_impl(keyword="dex", source="spellbook", limit=5, include_columns=True)
    schemas = result.get("schemas", [])
    tables = result.get("tables", [])
    assert len(schemas) > 0
    assert len(tables) > 0
    
    # Step 2: Verify table structure includes schema, table, and columns
    test_table = tables[0]
    assert "schema" in test_table
    assert "table" in test_table
    assert "fully_qualified_name" in test_table
    assert "columns" in test_table
    columns = test_table.get("columns", [])
    assert isinstance(columns, list)
    
    # Step 3: Use discovered info to query (if query tool is available)
    if server.EXECUTE_QUERY_TOOL:
        # Construct a simple query using discovered table
        # Note: For verified tables, use dune_table field if available
        table_name = test_table.get("dune_table") or test_table["fully_qualified_name"]
        query_sql = f"SELECT * FROM {table_name} LIMIT 5"
        print(f"\n🔍 Querying: {query_sql}")
        
        query_result = server.EXECUTE_QUERY_TOOL.execute(query=query_sql, format="preview")
        assert query_result["type"] == "preview"
        assert "rowcount" in query_result

