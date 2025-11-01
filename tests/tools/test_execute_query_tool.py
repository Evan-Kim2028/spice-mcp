from __future__ import annotations

from typing import Any

from spice_mcp.config import Config, DuneConfig
from spice_mcp.logging.query_history import DisabledQueryHistory, QueryHistory
from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool


class FakeQueryService:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []
        self.raise_exc: Exception | None = None

    def execute(
        self,
        *,
        query: str,
        parameters: dict[str, Any] | None = None,
        refresh: bool = False,
        max_age: float | None = None,
        poll: bool = True,
        timeout_seconds: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sample_count: int | None = None,
        sort_by: str | None = None,
        columns: list[str] | None = None,
        include_execution: bool = True,
        performance: str | None = None,
        return_raw: bool = False,
    ) -> dict[str, Any]:
        self.calls.append({"query": query, "params": parameters, "return_raw": return_raw})
        if self.raise_exc:
            raise self.raise_exc
        payload = {
            "rowcount": 2,
            "columns": ["a", "b"],
            "data_preview": [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}],
            "execution": {"execution_id": "e-xyz"},
            "duration_ms": 5,
        }
        if return_raw:
            payload["data"] = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        return payload


def test_execute_query_tool_happy_path(tmp_path):
    cfg = Config(dune=DuneConfig(api_key="k"))
    svc = FakeQueryService()
    hist = QueryHistory(tmp_path / "h.jsonl", tmp_path / "artifacts")

    tool = ExecuteQueryTool(cfg, svc, hist)

    out = asyncio_run(tool.execute(query="SELECT 1", limit=2, format="preview"))

    assert out["type"] == "preview"
    assert out["rowcount"] == 2
    assert out["columns"] == ["a", "b"]
    assert out["execution_id"] == "e-xyz"
    assert "metadata" in out  # may be None if fetch fails gracefully
    assert svc.calls[-1]["return_raw"] is False


def test_execute_query_tool_raw_format(tmp_path):
    cfg = Config(dune=DuneConfig(api_key="k"))
    svc = FakeQueryService()
    hist = QueryHistory(tmp_path / "h.jsonl", tmp_path / "artifacts")

    tool = ExecuteQueryTool(cfg, svc, hist)

    out = asyncio_run(tool.execute(query="SELECT 1", limit=2, format="raw"))

    assert out["type"] == "raw"
    assert out["data"] == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    assert out["data_preview"] == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    assert svc.calls[-1]["return_raw"] is True


def test_execute_query_tool_with_disabled_history():
    cfg = Config(dune=DuneConfig(api_key="k"))
    svc = FakeQueryService()
    hist = DisabledQueryHistory()

    tool = ExecuteQueryTool(cfg, svc, hist)

    out = asyncio_run(tool.execute(query="SELECT 1"))

    assert out["type"] == "preview"
    assert svc.calls[-1]["return_raw"] is False


def test_execute_query_tool_timeout_error(tmp_path):
    cfg = Config(dune=DuneConfig(api_key="k"))
    svc = FakeQueryService()
    svc.raise_exc = TimeoutError("timed out")
    hist = QueryHistory(tmp_path / "h.jsonl", tmp_path / "artifacts")

    tool = ExecuteQueryTool(cfg, svc, hist)

    out = asyncio_run(tool.execute(query="SELECT 1"))

    assert out["ok"] is False
    assert out["error"]["code"] == "QUERY_TIMEOUT"


def test_execute_query_tool_rate_limit(tmp_path):
    cfg = Config(dune=DuneConfig(api_key="k"))
    svc = FakeQueryService()
    svc.raise_exc = RuntimeError("429 rate limit exceeded")
    hist = QueryHistory(tmp_path / "h.jsonl", tmp_path / "artifacts")

    tool = ExecuteQueryTool(cfg, svc, hist)

    out = asyncio_run(tool.execute(query="SELECT 1"))

    assert out["ok"] is False
    assert out["error"]["code"] == "RATE_LIMIT"


def asyncio_run(coro):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        raise RuntimeError("asyncio_run should not be called from a running event loop")
    return asyncio.run(coro)
