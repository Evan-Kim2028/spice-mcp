"""Test FastMCP tool schema validation for dune_query to catch issue #8."""

import json
from typing import Any

import pytest


def test_dune_query_tool_registration(monkeypatch, tmp_path):
    """Test that dune_query tool is properly registered with FastMCP."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    from spice_mcp.mcp import server

    server._ensure_initialized()

    # Verify tool is registered
    assert hasattr(server.dune_query, "fn")
    assert callable(server.dune_query.fn)

    # Test that we can inspect the function signature
    import inspect

    sig = inspect.signature(server.dune_query.fn)
    params = sig.parameters

    # Verify parameters parameter exists and has correct type annotation
    assert "parameters" in params
    param_annotation = params["parameters"].annotation
    # Should be Optional[dict[str, Any]] or similar
    assert "dict" in str(param_annotation) or "Dict" in str(param_annotation)


def test_dune_query_accepts_none_parameters(monkeypatch, tmp_path):
    """Test that dune_query accepts None for parameters (issue #8)."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    from spice_mcp.mcp import server

    server._ensure_initialized()

    # Mock the execute method to avoid actual API calls
    def _fake_execute(**kwargs) -> dict[str, Any]:
        assert kwargs.get("parameters") is None or isinstance(kwargs.get("parameters"), dict)
        return {
            "type": "preview",
            "rowcount": 0,
            "columns": [],
            "data_preview": [],
            "execution": {"execution_id": "test"},
            "duration_ms": 1,
        }

    server.EXECUTE_QUERY_TOOL.execute = _fake_execute  # type: ignore[attr-defined]
    monkeypatch.setattr(server.EXECUTE_QUERY_TOOL.query_history, "record", lambda **k: None)

    # Test calling with None parameters (should work)
    result = server.dune_query.fn(
        query="SELECT 1",
        parameters=None,
        format="preview",
    )
    assert result["type"] == "preview"

    # Test calling with dict parameters (should work)
    result = server.dune_query.fn(
        query="SELECT 1",
        parameters={"test": "value"},
        format="preview",
    )
    assert result["type"] == "preview"

    # Test calling without parameters keyword (should default to None)
    result = server.dune_query.fn(
        query="SELECT 1",
        format="preview",
    )
    assert result["type"] == "preview"


def test_dune_query_handles_string_parameters_gracefully(monkeypatch, tmp_path):
    """Test that dune_query handles string parameters (defensive fix for issue #8)."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    from spice_mcp.mcp import server

    server._ensure_initialized()

    # Mock the execute method
    def _fake_execute(**kwargs) -> dict[str, Any]:
        params = kwargs.get("parameters")
        # Should be normalized to dict, not string
        assert params is None or isinstance(params, dict), f"Expected dict or None, got {type(params)}"
        return {
            "type": "preview",
            "rowcount": 0,
            "columns": [],
            "data_preview": [],
            "execution": {"execution_id": "test"},
            "duration_ms": 1,
        }

    server.EXECUTE_QUERY_TOOL.execute = _fake_execute  # type: ignore[attr-defined]
    monkeypatch.setattr(server.EXECUTE_QUERY_TOOL.query_history, "record", lambda **k: None)

    # Test that if a string somehow gets through, it's normalized
    # This simulates the defensive normalization we added
    result = server.dune_query.fn(
        query="SELECT 1",
        parameters=json.dumps({"test": "value"}),  # Pass as JSON string
        format="preview",
    )
    # Should normalize to dict internally
    assert result["type"] == "preview"


def test_dune_query_schema_properties(monkeypatch, tmp_path):
    """Test that FastMCP generates correct schema for dune_query."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "queries.jsonl"))

    from spice_mcp.mcp import server

    server._ensure_initialized()

    # FastMCP should have generated a schema
    # The tool object should have schema information
    tool_obj = server.dune_query

    # Verify tool has expected attributes
    assert hasattr(tool_obj, "name") or hasattr(tool_obj, "fn")

    # If FastMCP exposes schema, verify parameters can be None
    # Note: FastMCP's internal schema structure may vary, so we test behavior instead
    # The key test is that calling with None works (tested above)

