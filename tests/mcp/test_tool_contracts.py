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

    schemas_only = server._dune_find_tables_impl(keyword="sui")
    assert schemas_only["schemas"] == ["sui_base"]

    tables = server._dune_find_tables_impl(schema="sui_base")
    assert tables["tables"] == ["events"]

    desc = server._dune_describe_table_impl(schema="sui", table="events")
    assert desc["table"] == "sui.events"
    assert desc["columns"][0]["name"] == "col1"


@pytest.mark.mcp
def test_sui_tools_and_resources(mock_server):
    from spice_mcp.mcp import server

    overview_tool = server.SUI_OVERVIEW_TOOL.execute(packages=["0xabc"], hours=72, timeout_seconds=5)
    assert overview_tool["ok"] is True
    assert overview_tool["events_preview"]

    events_resource_raw = server.sui_events_preview_resource.fn("72", "50", "_")
    events = json.loads(events_resource_raw)
    assert events["ok"] is True
    assert events["rowcount"] == 50

    overview_resource_raw = server.sui_package_overview_cmd.fn("72", "30", "0xabc")
    overview = json.loads(overview_resource_raw)
    assert overview["ok"] is True
