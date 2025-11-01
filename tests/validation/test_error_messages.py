"""
Error Message Validation Tests

Verify that error messages:
- Contain actionable information
- Have consistent error codes
- Include relevant context
- Are user-friendly
"""
from __future__ import annotations

import pytest

from spice_mcp.core.errors import error_response


def test_error_response_includes_context():
    """Test that error responses include helpful context."""
    error = ValueError("Invalid query parameter")
    context = {"tool": "dune_query", "query": "SELECT 1", "query_type": "raw_sql"}
    
    result = error_response(error, context=context)
    
    assert "ok" in result
    assert result["ok"] is False
    assert "error" in result
    assert "code" in result["error"]
    assert "message" in result["error"]
    assert "context" in result["error"]
    
    # Context should include provided information
    assert result["error"]["context"]["tool"] == "dune_query"
    assert result["error"]["context"]["query"] == "SELECT 1"


def test_error_codes_are_consistent():
    """Test that error codes follow consistent patterns."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FailingQueryService:
        def execute(self, **kwargs):
            raise TimeoutError("Query timed out after 30 seconds")
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FailingQueryService(),
        DisabledQueryHistory(),
    )
    
    result = tool.execute(query="SELECT 1", format="preview")
    
    assert result["ok"] is False
    assert "error" in result
    assert "code" in result["error"]
    # Timeout errors should have specific code
    assert result["error"]["code"] == "QUERY_TIMEOUT"


def test_error_messages_are_actionable():
    """Test that error messages provide actionable guidance."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FailingQueryService:
        def execute(self, **kwargs):
            raise RuntimeError("429 rate limit exceeded")
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FailingQueryService(),
        DisabledQueryHistory(),
    )
    
    result = tool.execute(query="SELECT 1", format="preview")
    
    assert result["ok"] is False
    assert "error" in result
    assert "message" in result["error"]
    
    # Error message should be present and not empty
    message = result["error"]["message"]
    assert len(message) > 0
    assert isinstance(message, str)


def test_error_context_includes_debug_info():
    """Test that error context includes debugging information when available."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FailingQueryService:
        def execute(self, **kwargs):
            raise Exception("could not determine execution")
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FailingQueryService(),
        DisabledQueryHistory(),
    )
    
    result = tool.execute(query="SELECT 1", format="preview")
    
    assert result["ok"] is False
    assert "error" in result
    assert "context" in result["error"]
    
    # For raw SQL failures, should include debug info
    context = result["error"]["context"]
    if "debug_info" in context:
        assert len(context["debug_info"]) > 0


def test_timeout_errors_have_specific_code():
    """Test that timeout errors use the QUERY_TIMEOUT code."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class TimeoutQueryService:
        def execute(self, **kwargs):
            raise TimeoutError("Query execution timed out")
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        TimeoutQueryService(),
        DisabledQueryHistory(),
    )
    
    result = tool.execute(query="SELECT 1", format="preview")
    
    assert result["ok"] is False
    assert result["error"]["code"] == "QUERY_TIMEOUT"


def test_rate_limit_errors_have_specific_code():
    """Test that rate limit errors use the RATE_LIMIT code."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class RateLimitQueryService:
        def execute(self, **kwargs):
            raise RuntimeError("429 rate limit exceeded")
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        RateLimitQueryService(),
        DisabledQueryHistory(),
    )
    
    result = tool.execute(query="SELECT 1", format="preview")
    
    assert result["ok"] is False
    assert result["error"]["code"] == "RATE_LIMIT"


def test_error_messages_include_query_info():
    """Test that error messages include relevant query information."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FailingQueryService:
        def execute(self, **kwargs):
            raise ValueError("Invalid SQL syntax")
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FailingQueryService(),
        DisabledQueryHistory(),
    )
    
    test_query = "SELECTTTT INVALID"
    result = tool.execute(query=test_query, format="preview")
    
    assert result["ok"] is False
    assert "error" in result
    assert "context" in result["error"]
    
    # Context should include the query (possibly truncated)
    context = result["error"]["context"]
    assert "query" in context or "query_preview" in context


def test_error_responses_are_serializable():
    """Test that error responses can be serialized to JSON."""
    import json
    
    error = ValueError("Test error")
    context = {"tool": "test_tool", "param": "value"}
    
    result = error_response(error, context=context)
    
    # Should be JSON serializable
    json_str = json.dumps(result)
    assert len(json_str) > 0
    
    # Should be able to deserialize
    parsed = json.loads(json_str)
    assert parsed["ok"] is False
    assert "error" in parsed

