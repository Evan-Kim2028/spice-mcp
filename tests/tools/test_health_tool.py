from __future__ import annotations

from spice_mcp.config import Config, DuneConfig
from spice_mcp.logging.query_history import QueryHistory
from spice_mcp.mcp import server


def test_health_tool_flags(tmp_path, monkeypatch):
    # No env API key, but config provides one
    monkeypatch.delenv("DUNE_API_KEY", raising=False)
    cfg = Config(dune=DuneConfig(api_key="local_key"))
    # prime server CONFIG and history so compute_health_status can read config fallback
    server.CONFIG = cfg
    server.QUERY_HISTORY = QueryHistory(tmp_path / "h.jsonl", tmp_path / "artifacts")

    out = server.compute_health_status()

    assert out["api_key_present"] is True
    assert out["query_history_path"].endswith("h.jsonl")
    assert out["status"] in ("ok", "degraded")
    # ensure degraded when env key missing but config present still counts
