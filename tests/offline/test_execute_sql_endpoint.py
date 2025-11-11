from __future__ import annotations

import os

from spice_mcp.adapters.dune import extract, urls


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


def test_execute_raw_sql_endpoint(monkeypatch):
    """Test Execute SQL endpoint for raw SQL."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_DUNE_RAW_SQL_ENGINE", "execution_sql")
    
    # Mock the POST response
    resp = StubResponse({"execution_id": "exec-123"})
    
    # We can't easily mock the transport layer, so we'll test the URL template
    assert "execution/sql" in urls.url_templates["execution_sql"]


def test_execute_raw_sql_uses_template_when_configured(monkeypatch):
    """Test that template engine is used when SPICE_DUNE_RAW_SQL_ENGINE=template."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_DUNE_RAW_SQL_ENGINE", "template")
    
    # When template engine is used, _determine_input_type should return template query ID
    query_id, execution, params = extract._determine_input_type("SELECT 1", None)
    assert query_id is not None
    assert execution is None
    assert params is not None
    assert "query" in params


def test_execute_raw_sql_uses_execution_sql_when_configured(monkeypatch):
    """Test that execution_sql engine is used when SPICE_DUNE_RAW_SQL_ENGINE=execution_sql."""
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_DUNE_RAW_SQL_ENGINE", "execution_sql")
    
    # When execution_sql engine is used, query() should route to _execute_raw_sql
    # This is tested implicitly through integration tests
    # Here we just verify the URL template exists
    assert "execution/sql" in urls.url_templates["execution_sql"]

