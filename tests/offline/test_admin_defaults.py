from __future__ import annotations

from spice_mcp.adapters.dune.admin import DuneAdminAdapter
from spice_mcp.service_layer.query_admin_service import QueryAdminService


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


def test_create_auto_tags_when_none_provided():
    """Test that queries are auto-tagged with 'spice-mcp' when tags not provided."""
    resp = StubResponse({"query_id": 12345, "name": "Test Query"})
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    adapter.create(name="Test", query_sql="SELECT 1")

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    body = kwargs.get("json", {})
    assert body.get("tags") == ["spice-mcp"]


def test_create_preserves_provided_tags():
    """Test that provided tags are preserved."""
    resp = StubResponse({"query_id": 12345, "name": "Test Query"})
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)

    adapter.create(name="Test", query_sql="SELECT 1", tags=["custom", "tags"])

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    body = kwargs.get("json", {})
    assert body.get("tags") == ["custom", "tags"]


def test_service_force_private():
    """Test that QueryAdminService respects force_private flag."""
    resp = StubResponse({"query_id": 12345, "name": "Test Query"})
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)
    service = QueryAdminService(adapter, force_private=True)

    service.create(name="Test", query_sql="SELECT 1")

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    body = kwargs.get("json", {})
    assert body.get("is_private") is True


def test_service_force_private_always_applies():
    """Test that force_private always applies, even with explicit is_private=False."""
    resp = StubResponse({"query_id": 12345, "name": "Test Query"})
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)
    service = QueryAdminService(adapter, force_private=True)

    # When force_private=True, it always overrides any explicit is_private value
    service.create(name="Test", query_sql="SELECT 1", is_private=False)

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    body = kwargs.get("json", {})
    # force_private=True should override explicit is_private=False
    assert body.get("is_private") is True


def test_service_no_force_private_defaults_to_public():
    """Test that without force_private, queries default to public."""
    resp = StubResponse({"query_id": 12345, "name": "Test Query"})
    client = StubHttpClient([resp])
    adapter = DuneAdminAdapter("test-key", http_client=client)
    service = QueryAdminService(adapter, force_private=False)

    service.create(name="Test", query_sql="SELECT 1")

    assert len(client.calls) == 1
    method, url, kwargs = client.calls[0]
    body = kwargs.get("json", {})
    # Default should be False (public)
    assert body.get("is_private") is False

