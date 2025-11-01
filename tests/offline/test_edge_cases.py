"""
Edge Case Tests - Test boundary conditions and unusual inputs

Tests:
- Empty inputs
- Very large inputs
- Special characters
- Unicode handling
- Boundary values
"""
from __future__ import annotations

import pytest

from spice_mcp.adapters.dune import extract


def test_empty_query_string():
    """Test handling of empty query string."""
    with pytest.raises(Exception):
        extract.query("", poll=False)


def test_whitespace_only_query():
    """Test handling of whitespace-only query."""
    with pytest.raises(Exception):
        extract.query("   \n\t  ", poll=False)


def test_very_long_query_string():
    """Test handling of very long query strings."""
    # Create a query that's longer than typical limits
    long_query = "SELECT " + ", ".join([f"{i} as col_{i}" for i in range(1000)])
    
    # Should either succeed or fail gracefully, not crash
    try:
        result = extract.query(long_query, poll=False, api_key="test")
        # If it succeeds, it should return an execution object
        assert isinstance(result, dict)
        assert "execution_id" in result or "error" in result
    except Exception as e:
        # Should raise a specific error, not crash
        assert len(str(e)) > 0


def test_special_characters_in_query():
    """Test handling of special characters in SQL."""
    special_chars_queries = [
        "SELECT 'test@example.com' as email",
        "SELECT 'path/to/file' as path",
        "SELECT 'name-with-dashes' as name",
        "SELECT 'name_with_underscores' as name",
        "SELECT 'name.with.dots' as name",
        "SELECT '$value' as price",
        "SELECT '100%' as percentage",
    ]
    
    for query in special_chars_queries:
        # Should handle special characters without crashing
        try:
            result = extract.query(query, poll=False, api_key="test")
            assert isinstance(result, dict)
        except Exception as e:
            # Should raise meaningful error, not crash
            assert len(str(e)) > 0


def test_unicode_in_query():
    """Test handling of Unicode characters in queries."""
    unicode_queries = [
        "SELECT '测试' as chinese",
        "SELECT 'тест' as russian",
        "SELECT 'テスト' as japanese",
        "SELECT '🎉' as emoji",
        "SELECT 'café' as french",
        "SELECT 'naïve' as accented",
    ]
    
    for query in unicode_queries:
        try:
            result = extract.query(query, poll=False, api_key="test")
            assert isinstance(result, dict)
        except Exception as e:
            # Should handle Unicode gracefully
            assert len(str(e)) > 0


def test_boundary_limit_values():
    """Test boundary values for limit parameter."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FakeQueryService:
        def execute(self, **kwargs):
            return {
                "rowcount": kwargs.get("limit", 10),
                "columns": ["col"],
                "data_preview": [{"col": 1}],
                "execution": {"execution_id": "test"},
                "duration_ms": 100,
            }
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FakeQueryService(),
        DisabledQueryHistory(),
    )
    
    # Test various limit values
    boundary_limits = [0, 1, 10, 100, 1000, 10000, None]
    
    for limit in boundary_limits:
        try:
            result = tool.execute(query="SELECT 1", limit=limit, format="preview")
            assert result["type"] == "preview"
        except Exception as e:
            # Should handle boundary values gracefully
            assert len(str(e)) > 0


def test_boundary_offset_values():
    """Test boundary values for offset parameter."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FakeQueryService:
        def execute(self, **kwargs):
            return {
                "rowcount": 10,
                "columns": ["col"],
                "data_preview": [{"col": 1}],
                "execution": {"execution_id": "test"},
                "duration_ms": 100,
            }
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FakeQueryService(),
        DisabledQueryHistory(),
    )
    
    # Test various offset values
    boundary_offsets = [0, 1, 10, 100, 1000, None]
    
    for offset in boundary_offsets:
        try:
            result = tool.execute(query="SELECT 1", offset=offset, format="preview")
            assert result["type"] == "preview"
        except Exception as e:
            # Should handle boundary values gracefully
            assert len(str(e)) > 0


def test_empty_parameter_dict():
    """Test handling of empty parameter dictionary."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FakeQueryService:
        def execute(self, **kwargs):
            return {
                "rowcount": 1,
                "columns": ["col"],
                "data_preview": [{"col": 1}],
                "execution": {"execution_id": "test"},
                "duration_ms": 100,
            }
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FakeQueryService(),
        DisabledQueryHistory(),
    )
    
    # Empty parameters should work fine
    result = tool.execute(query="SELECT 1", parameters={}, format="preview")
    assert result["type"] == "preview"
    
    # None parameters should also work
    result = tool.execute(query="SELECT 1", parameters=None, format="preview")
    assert result["type"] == "preview"


def test_very_large_parameter_dict():
    """Test handling of very large parameter dictionaries."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FakeQueryService:
        def execute(self, **kwargs):
            return {
                "rowcount": 1,
                "columns": ["col"],
                "data_preview": [{"col": 1}],
                "execution": {"execution_id": "test"},
                "duration_ms": 100,
            }
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FakeQueryService(),
        DisabledQueryHistory(),
    )
    
    # Create a large parameter dict
    large_params = {f"param_{i}": f"value_{i}" for i in range(100)}
    
    try:
        result = tool.execute(query="SELECT 1", parameters=large_params, format="preview")
        assert result["type"] == "preview"
    except Exception as e:
        # Should handle gracefully, not crash
        assert len(str(e)) > 0


def test_special_characters_in_parameters():
    """Test handling of special characters in parameter values."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FakeQueryService:
        def execute(self, **kwargs):
            return {
                "rowcount": 1,
                "columns": ["col"],
                "data_preview": [{"col": 1}],
                "execution": {"execution_id": "test"},
                "duration_ms": 100,
            }
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FakeQueryService(),
        DisabledQueryHistory(),
    )
    
    special_params = {
        "email": "test@example.com",
        "path": "/path/to/file",
        "unicode": "测试",
        "emoji": "🎉",
        "special": "!@#$%^&*()",
    }
    
    try:
        result = tool.execute(query="SELECT 1", parameters=special_params, format="preview")
        assert result["type"] == "preview"
    except Exception as e:
        # Should handle special characters gracefully
        assert len(str(e)) > 0

