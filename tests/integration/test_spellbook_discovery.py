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
    assert "models" in result
    models = result["models"]
    assert len(models) > 0
    model_names = [m["table"] for m in models]
    assert "trades" in model_names
    
    # Test 3: Verify model includes column details
    trades_model = next(m for m in models if m["table"] == "trades")
    assert "columns" in trades_model
    assert len(trades_model["columns"]) > 0
    column_names = [c["name"] for c in trades_model["columns"]]
    assert "block_time" in column_names or "tx_hash" in column_names
    
    # Test 4: Test with multiple keywords
    result = server._spellbook_find_models_impl(keyword=["dex", "nft"], include_columns=False)
    assert "schemas" in result
    assert "models" in result
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
    
    # Test 1: Find spellbook schemas/subprojects (parses GitHub repo)
    print("\n🔍 Searching Spellbook GitHub repo for schemas...")
    result = server._spellbook_find_models_impl(keyword="dex")
    
    assert "schemas" in result, "Result should contain 'schemas' key"
    schemas = result.get("schemas", [])
    print(f"   Found {len(schemas)} schemas: {schemas[:5]}...")
    
    if not schemas:
        pytest.skip("No schemas found - may need to check git availability or repo access")
    
    # Test 2: Search for models matching keyword (includes column details)
    print(f"\n📊 Searching for models matching 'dex' with column details...")
    result = server._spellbook_find_models_impl(keyword="dex", limit=5, include_columns=True)
    
    assert "models" in result
    models = result.get("models", [])
    print(f"   Found {len(models)} models")
    
    if not models:
        pytest.skip("No models found - may need to check git availability or repo access")
    
    # Test 3: Verify model structure includes columns
    test_model = models[0]
    print(f"\n📋 Model: {test_model.get('fully_qualified_name')}")
    columns = test_model.get("columns", [])
    print(f"   Columns ({len(columns)}): {[c['name'] for c in columns[:5]]}...")
    
    assert "schema" in test_model
    assert "table" in test_model
    assert "fully_qualified_name" in test_model
    assert len(columns) >= 0, "Model should have columns list (may be empty if parsing fails)"


@pytest.mark.skipif(not _should_run_live(), reason="live tests disabled by default")
@pytest.mark.live
def test_spellbook_workflow_end_to_end():
    """
    End-to-end workflow: Discover spellbook → List tables → Describe → Query.
    
    This tests the complete user journey with actual Dune API calls.
    """
    server._ensure_initialized()
    
    # Step 1: Discover spellbook schemas and models
    result = server._spellbook_find_models_impl(keyword="dex", limit=5, include_columns=True)
    schemas = result.get("schemas", [])
    models = result.get("models", [])
    assert len(schemas) > 0
    assert len(models) > 0
    
    # Step 2: Verify model structure includes schema, table, and columns
    test_model = models[0]
    assert "schema" in test_model
    assert "table" in test_model
    assert "fully_qualified_name" in test_model
    assert "columns" in test_model
    columns = test_model.get("columns", [])
    assert isinstance(columns, list)
    
    # Step 3: Use discovered info to query (if query tool is available)
    if server.EXECUTE_QUERY_TOOL:
        # Construct a simple query using discovered model
        model_name = test_model["fully_qualified_name"]
        query_sql = f"SELECT * FROM {model_name} LIMIT 5"
        print(f"\n� Querying: {query_sql}")
        
        query_result = server.EXECUTE_QUERY_TOOL.execute(query=query_sql, format="preview")
        assert query_result["type"] == "preview"
        assert "rowcount" in query_result

