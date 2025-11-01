from typing import Any

import pytest


def test_fastmcp_startup_initializes_tools(monkeypatch, tmp_path):
    # Arrange: ensure env for Config/QueryHistory and isolate logs to tmp
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    # Import after env is set
    from spice_mcp.mcp import server

    # Act: force init
    server._ensure_initialized()

    # Assert: tool instances created
    assert server.EXECUTE_QUERY_TOOL is not None
    assert server.SUI_OVERVIEW_TOOL is not None


def test_health_tool_executes(monkeypatch, tmp_path):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    from spice_mcp.mcp import server

    server._ensure_initialized()

    # Execute health logic without requiring full init
    result = server.compute_health_status()
    assert isinstance(result, dict)
    assert "status" in result
    assert "api_key_present" in result


def test_dune_query_delegates_and_returns_preview(monkeypatch, tmp_path):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    from spice_mcp.mcp import server

    server._ensure_initialized()

    # Stub out network-bound pieces
    assert server.EXECUTE_QUERY_TOOL is not None

    # Avoid calling vendored spice; return a minimal, valid result
    def _fake_execute(**kwargs) -> dict[str, Any]:
        return {
            "rowcount": 2,
            "columns": ["a", "b"],
            "data_preview": [{"a": 1, "b": 2}, {"a": 3, "b": 4}],
            "execution": {"execution_id": "test-exec"},
            "duration_ms": 5,
            "metadata": {"state": "finished"},
        }

    # Monkeypatch the bound service on the tool instance
    server.EXECUTE_QUERY_TOOL.query_service.execute = _fake_execute  # type: ignore[attr-defined]

    # Also stub query_history.record to avoid file writes assertion
    monkeypatch.setattr(server.EXECUTE_QUERY_TOOL.query_history, "record", lambda **k: None)

    # Act: call underlying tool directly to avoid FastMCP internals
    res = server.EXECUTE_QUERY_TOOL.execute(query="select 1", format="preview")  # type: ignore[union-attr]

    # Assert
    assert res["type"] == "preview"
    assert res["rowcount"] == 2
    assert res["columns"] == ["a", "b"]
    assert res["execution_id"] == "test-exec"


def test_fastmcp_registers_tools_and_schemas(monkeypatch, tmp_path):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    from spice_mcp.mcp import server

    server._ensure_initialized()

    # App should expose tools with generated schemas
    tool = server.app.get_tool("dune_query")
    assert tool.name == "dune_query"
    # Tools list should include our registered tools
    tools = server.app.get_tools()
    names = set(tools.keys())
    for n in {"dune_query", "dune_health_check", "dune_find_tables", "dune_describe_table", "sui_package_overview"}:
        assert n in names


def test_server_registration_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))

    from spice_mcp.mcp import server

    server.CONFIG = None
    server.EXECUTE_QUERY_TOOL = None
    server.SUI_OVERVIEW_TOOL = None
    server.QUERY_HISTORY = None
    server.DUNE_ADAPTER = None
    server.QUERY_SERVICE = None
    server.DISCOVERY_SERVICE = None
    server.SUI_SERVICE = None

    server._ensure_initialized()

    assert server.app.name == "spice-mcp"

    tools = server.app.get_tools()
    assert set(tools.keys()) >= {"dune_query", "dune_find_tables", "dune_describe_table"}

    resources = server.app.get_resource_templates()
    assert "spice:sui/events_preview/{hours}/{limit}/{packages}" in resources
    assert "spice:sui/package_overview/{hours}/{timeout_seconds}/{packages}" in resources
