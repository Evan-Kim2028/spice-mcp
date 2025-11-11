from __future__ import annotations

from spice_mcp.adapters.dune.admin import DuneAdminAdapter
from spice_mcp.adapters.http_client import HttpClientConfig


class StubResponse:
    def __init__(self, data, *, status: int = 200, headers: dict | None = None, text: str | None = None):
        self._data = data
        self.status_code = status
        self.headers = headers or {}
        self.text = text or ""
        self.ok = status < 400

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


def test_archive_success():
    """Test successful archive operation."""
    resp = StubResponse({"query_id": 12345, "status": "archived"})
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    result = adapter.archive(12345)

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert "/query/12345/archive" in url
    assert kwargs["headers"]["X-Dune-API-Key"] == "test-key"
    assert result["query_id"] == 12345
    assert result["status"] == "archived"


def test_unarchive_success():
    """Test successful unarchive operation."""
    resp = StubResponse({"query_id": 12345, "status": "unarchived"})
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    result = adapter.unarchive(12345)

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert "/query/12345/unarchive" in url
    assert kwargs["headers"]["X-Dune-API-Key"] == "test-key"
    assert result["query_id"] == 12345
    assert result["status"] == "unarchived"


def test_archive_handles_404():
    """Test archive handles 404 (query not found)."""
    resp = StubResponse({"error": "Query not found"}, status=404)
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    result = adapter.archive(99999)

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert "/query/99999/archive" in url
    assert result["error"] == "Query not found"


def test_unarchive_handles_404():
    """Test unarchive handles 404 (query not found)."""
    resp = StubResponse({"error": "Query not found"}, status=404)
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    result = adapter.unarchive(99999)

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert "/query/99999/unarchive" in url
    assert result["error"] == "Query not found"


def test_archive_handles_400():
    """Test archive handles 400 (bad request)."""
    resp = StubResponse({"error": "Invalid request"}, status=400)
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    result = adapter.archive(12345)

    assert len(client.calls) == 1
    assert result["error"] == "Invalid request"


def test_unarchive_handles_400():
    """Test unarchive handles 400 (bad request)."""
    resp = StubResponse({"error": "Invalid request"}, status=400)
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    result = adapter.unarchive(12345)

    assert len(client.calls) == 1
    assert result["error"] == "Invalid request"

