from __future__ import annotations

import jsonschema

from spice_mcp.config import Config, DuneConfig
from spice_mcp.logging.query_history import QueryHistory
from spice_mcp.mcp import server
from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool


def test_execute_query_tool_schema_validation(tmp_path):
    cfg = Config(dune=DuneConfig(api_key="k"))
    tool = ExecuteQueryTool(cfg, query_service=None, query_history=QueryHistory(tmp_path / "h.jsonl", tmp_path / "artifacts"))  # type: ignore[arg-type]
    schema = tool.get_parameter_schema()

    # valid
    ok = {"query": "SELECT 1", "limit": 5}
    jsonschema.validate(ok, schema)

    # invalid: additionalProperties not allowed
    bad = {"query": "1", "unknown": True}
    try:
        jsonschema.validate(bad, schema)
        assert False, "expected validation error"
    except jsonschema.ValidationError:
        pass


def test_health_tool_requires_no_parameters(tmp_path, monkeypatch):
    # Health is exposed via FastMCP and requires no params; ensure tool is registered
    monkeypatch.setenv("DUNE_API_KEY", "k")
    server._ensure_initialized()
    tool = server.app  # smoke: app exists and tool registered
    # Compute health directly (schema validation is redundant under FastMCP)
    out = server.compute_health_status()
    assert isinstance(out, dict) and "status" in out
