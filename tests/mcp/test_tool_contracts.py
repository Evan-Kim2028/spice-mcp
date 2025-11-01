from __future__ import annotations

import json

import pytest


@pytest.mark.mcp
def test_dune_query_variants(mock_server):
    from spice_mcp.mcp import server

    preview = server.EXECUTE_QUERY_TOOL.execute(query="SELECT 1", limit=1, format="preview")
    assert preview["type"] == "preview"
    assert preview["rowcount"] == 1

    raw = server.EXECUTE_QUERY_TOOL.execute(query="SELECT 1", limit=1, format="raw")
    assert raw["type"] == "raw"
    assert raw["data"] == [{"_col0": 1}]

    metadata = server.EXECUTE_QUERY_TOOL.execute(query="SELECT 1", format="metadata")
    assert metadata["type"] == "metadata"
    assert metadata["metadata"]["state"] == "ok"


@pytest.mark.mcp
def test_discovery_tools(mock_server):
    from spice_mcp.mcp import server

    schemas_only = server._unified_discover_impl(keyword="sui", source="dune")
    assert "sui_base" in schemas_only["schemas"]

    tables = server._unified_discover_impl(schema="sui_base", source="dune")
    assert len(tables["tables"]) > 0
    assert tables["tables"][0]["table"] == "events"

    desc = server._dune_describe_table_impl(schema="sui", table="events")
    assert desc["table"] == "sui.events"
    assert desc["columns"][0]["name"] == "col1"


