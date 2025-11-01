from __future__ import annotations

from spice_mcp.mcp.tools.execute_query import _maybe_rewrite_show_sql


def test_rewrite_show_schemas_like():
    """Test that rewrite function is deprecated and returns None.
    
    Native SHOW statements are now used directly (faster than information_schema).
    See issue #10.
    """
    sql = "SHOW SCHEMAS LIKE '%layerzero%'"
    out = _maybe_rewrite_show_sql(sql)
    assert out is None  # Function is deprecated and disabled


def test_rewrite_show_schemas():
    """Test that rewrite function is deprecated and returns None.
    
    Native SHOW statements are now used directly (faster than information_schema).
    See issue #10.
    """
    sql = "SHOW SCHEMAS;"
    out = _maybe_rewrite_show_sql(sql)
    assert out is None  # Function is deprecated and disabled


def test_rewrite_show_tables_from():
    """Test that rewrite function is deprecated and returns None.
    
    Native SHOW statements are now used directly (faster than information_schema).
    See issue #10.
    """
    sql = "SHOW TABLES FROM layerzero_core"
    out = _maybe_rewrite_show_sql(sql)
    assert out is None  # Function is deprecated and disabled

