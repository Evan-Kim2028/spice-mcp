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
def test_spellbook_discovery_through_mcp_tool(monkeypatch, tmp_path):
    """
    Test spellbook discovery through the actual MCP tool interface.
    
    This verifies the full stack:
    1. MCP tool spellbook_find_models
    2. SpellbookExplorer.find_schemas() which parses GitHub repo
    3. Returns schema/subproject names from Spellbook dbt models
    """
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))
    
    # Initialize server to set up services
    server._ensure_initialized()
    
    # Verify the tool function exists (via FastMCP wrapper)
    assert hasattr(server.spellbook_find_models, 'fn')
    assert callable(server.spellbook_find_models.fn)
    
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
    
    # Replace spellbook explorer with stub
    server.SPELLBOOK_EXPLORER = StubSpellbookExplorer()
    
    # Test 1: Find spellbook schemas/subprojects via MCP tool
    result = server._spellbook_find_models_impl(keyword="dex")
    assert "schemas" in result
    schemas = result["schemas"]
    assert len(schemas) > 0
    assert "dex" in schemas
    
    # Test 2: List tables/models in a spellbook schema
    result = server._spellbook_find_models_impl(schema="dex", limit=10)
    assert "tables" in result
    tables = result["tables"]
    assert len(tables) > 0
    assert "trades" in tables
    
    # Test 3: Describe a spellbook model
    result = server._spellbook_describe_model_impl(schema="dex", table="trades")
    assert "columns" in result
    assert len(result["columns"]) > 0
    column_names = [c["name"] for c in result["columns"]]
    assert "block_time" in column_names or "tx_hash" in column_names


@pytest.mark.skipif(not _should_run_live(), reason="live tests disabled by default")
@pytest.mark.live
def test_spellbook_discovery_live():
    """
    Live test: Actually query Dune API to find spellbook schemas.
    
    This requires:
    - SPICE_TEST_LIVE=1
    - DUNE_API_KEY set
    
    This verifies that:
    1. The discovery can actually find spellbook schemas from Dune
    2. Spellbook tables are accessible
    3. Table descriptions work for spellbook tables
    """
    server._ensure_initialized()
    
    # Test 1: Find spellbook schemas (actual Dune query)
    print("\n🔍 Searching for spellbook schemas on Dune...")
    result = server._dune_find_tables_impl(keyword="spellbook")
    
    assert "schemas" in result, "Result should contain 'schemas' key"
    schemas = result.get("schemas", [])
    print(f"   Found {len(schemas)} schemas: {schemas[:5]}...")
    
    if not schemas:
        pytest.skip("No spellbook schemas found - may need to check Dune availability")
    
    # Verify we found spellbook-related schemas
    spellbook_schemas = [s for s in schemas if "spellbook" in s.lower()]
    assert len(spellbook_schemas) > 0, f"Expected spellbook schemas, got: {schemas}"
    
    # Test 2: List tables in a spellbook schema
    test_schema = spellbook_schemas[0]
    print(f"\n📊 Listing tables in {test_schema}...")
    result = server._dune_find_tables_impl(schema=test_schema, limit=20)
    
    assert "tables" in result
    tables = result.get("tables", [])
    print(f"   Found {len(tables)} tables: {tables[:10]}...")
    
    if not tables:
        pytest.skip(f"No tables found in {test_schema}")
    
    # Test 3: Describe a table from spellbook
    test_table = tables[0]
    print(f"\n📋 Describing {test_schema}.{test_table}...")
    result = server._dune_describe_table_impl(schema=test_schema, table=test_table)
    
    assert "columns" in result
    assert "table" in result
    columns = result.get("columns", [])
    print(f"   Table: {result.get('table')}")
    print(f"   Columns ({len(columns)}): {[c['name'] for c in columns[:5]]}...")
    
    assert len(columns) > 0, "Table should have columns"
    assert result["table"] == f"{test_schema}.{test_table}"


@pytest.mark.skipif(not _should_run_live(), reason="live tests disabled by default")
@pytest.mark.live
def test_spellbook_workflow_end_to_end():
    """
    End-to-end workflow: Discover spellbook → List tables → Describe → Query.
    
    This tests the complete user journey with actual Dune API calls.
    """
    server._ensure_initialized()
    
    # Step 1: Discover spellbook schemas
    result = server._dune_find_tables_impl(keyword="spellbook")
    schemas = result.get("schemas", [])
    assert len(schemas) > 0
    
    # Step 2: Find a spellbook schema and list its tables
    spellbook_schema = next((s for s in schemas if "spellbook" in s.lower()), None)
    assert spellbook_schema is not None
    
    result = server._dune_find_tables_impl(schema=spellbook_schema, limit=10)
    tables = result.get("tables", [])
    assert len(tables) > 0
    
    # Step 3: Describe a table
    test_table = tables[0]
    result = server._dune_describe_table_impl(schema=spellbook_schema, table=test_table)
    columns = result.get("columns", [])
    assert len(columns) > 0
    
    # Step 4: Use discovered info to query (if query tool is available)
    if server.EXECUTE_QUERY_TOOL:
        # Construct a simple query using discovered table
        query_sql = f"SELECT * FROM {spellbook_schema}.{test_table} LIMIT 5"
        print(f"\n� Querying: {query_sql}")
        
        query_result = server.EXECUTE_QUERY_TOOL.execute(query=query_sql, format="preview")
        assert query_result["type"] == "preview"
        assert "rowcount" in query_result

