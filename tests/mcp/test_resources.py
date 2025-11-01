from __future__ import annotations

import json

import pytest


class StubSuiService:
    def __init__(self, payload: dict[str, object], *, raise_error: Exception | None = None):
        self.payload = payload
        self.raise_error = raise_error
        self.calls = []

    def events_preview(self, packages, *, hours: int, limit: int):
        self.calls.append((tuple(packages), hours, limit))
        if self.raise_error:
            raise self.raise_error
        return self.payload


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_sui_events_preview_resource_success(monkeypatch):
    from spice_mcp.mcp import server

    stub = StubSuiService({"rowcount": 1, "columns": ["package"], "data_preview": [{"package": "0x1"}]})
    monkeypatch.setattr(server, "_ensure_initialized", lambda: None)
    server.SUI_SERVICE = stub  # type: ignore[assignment]

    raw = await server.sui_events_preview_resource.fn("72", "50", "0xabc")
    resp = json.loads(raw)

    assert resp["ok"] is True
    assert resp["rowcount"] == 1
    assert stub.calls == [(('0xabc',), 72, 50)]


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_sui_events_preview_resource_error(monkeypatch):
    from spice_mcp.mcp import server

    stub = StubSuiService({}, raise_error=RuntimeError("boom"))
    monkeypatch.setattr(server, "_ensure_initialized", lambda: None)
    server.SUI_SERVICE = stub  # type: ignore[assignment]

    raw = await server.sui_events_preview_resource.fn("invalid", "bad", "_")
    resp = json.loads(raw)

    assert resp["ok"] is False
    assert resp["error"]["code"] == "UNKNOWN_ERROR"
    assert resp["error"]["context"]["packages"] == []
    assert stub.calls == [((), 72, 50)]
