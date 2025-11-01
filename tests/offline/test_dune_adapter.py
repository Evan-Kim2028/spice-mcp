from __future__ import annotations

import polars as pl

from spice_mcp.adapters.dune.client import DuneAdapter
from spice_mcp.config import CacheConfig, Config, DuneConfig
from spice_mcp.core.models import QueryRequest, ResultMetadata


class StubResponse:
    def __init__(self, data, *, status: int = 200, headers: dict | None = None, text: str | None = None):
        self._data = data
        self.status_code = status
        self.headers = headers or {}
        self.text = text or ""

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


class StubHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("No stubbed responses remaining")
        return self.responses.pop(0)


def _make_config(tmp_path) -> Config:
    return Config(
        dune=DuneConfig(api_key="test-key"),
        cache=CacheConfig(cache_dir=str(tmp_path)),
    )


def test_fetch_metadata_handles_pagination(monkeypatch, tmp_path):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")

    resp = StubResponse(
        {
            "result": {"metadata": {"row_count": 42}},
            "next_uri": "https://api.dune.com/next/page",
            "next_offset": 128,
            "state": "QUERY_STATE_COMPLETED",
        }
    )
    client = StubHttpClient([resp])
    adapter = DuneAdapter(_make_config(tmp_path), http_client=client)

    request = QueryRequest(query="123", limit=10, offset=5)
    meta = adapter.fetch_metadata(request)

    method, url, kwargs = client.calls[0]
    assert method == "GET"
    assert "123" in url
    assert kwargs["headers"]["X-Dune-API-Key"] == "test-key"
    assert meta.metadata == {"row_count": 42, "state": "QUERY_STATE_COMPLETED"}
    assert meta.next_uri == "https://api.dune.com/next/page"
    assert meta.next_offset == 128
    assert meta.execution == {}


def test_execute_merges_preview_and_metadata(monkeypatch, tmp_path):
    adapter = DuneAdapter(_make_config(tmp_path))
    monkeypatch.setenv("DUNE_API_KEY", "test-key")

    def fake_query(query_or_execution, **kwargs):
        df = pl.DataFrame({"a": [1], "b": ["x"]})
        execution = {"execution_id": "exec-1", "timestamp": 1700000000}
        return df, execution

    def fake_fetch_metadata(self, request, *, execution=None):
        return ResultMetadata(
            execution=execution or {},
            duration_ms=0,
            metadata={"row_count": 1},
            next_offset=10,
            next_uri="https://api.dune.com/next",
        )

    monkeypatch.setattr("spice_mcp.adapters.dune.client.extract.query", fake_query)
    monkeypatch.setattr(DuneAdapter, "fetch_metadata", fake_fetch_metadata)

    request = QueryRequest(query="123", limit=5)
    result = adapter.execute(request)

    assert result.preview.rowcount == 1
    assert result.preview.columns == ["a", "b"]
    assert result.preview.data_preview == [{"a": 1, "b": "x"}]
    assert result.lazyframe is not None
    assert result.lazyframe.collect().to_dicts() == [{"a": 1, "b": "x"}]
    assert result.info.execution["execution_id"] == "exec-1"
    assert result.info.metadata == {"row_count": 1}
    assert result.info.next_uri == "https://api.dune.com/next"
    assert result.info.next_offset == 10


def test_fetch_metadata_handles_http_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")

    resp = StubResponse(ValueError("invalid json"))
    adapter = DuneAdapter(_make_config(tmp_path), http_client=StubHttpClient([resp]))

    request = QueryRequest(query="SELECT 1")
    meta = adapter.fetch_metadata(request)

    assert meta.metadata is None
    assert meta.next_uri is None
    assert meta.next_offset is None
