from __future__ import annotations

from spice_mcp.mcp.tools.execute_query import _maybe_rewrite_show_sql


def test_rewrite_show_schemas_like():
    sql = "SHOW SCHEMAS LIKE '%layerzero%'"
    out = _maybe_rewrite_show_sql(sql)
    assert out is not None
    assert "information_schema.schemata" in out
    assert "LIKE '%layerzero%'" in out


def test_rewrite_show_schemas():
    sql = "SHOW SCHEMAS;"
    out = _maybe_rewrite_show_sql(sql)
    assert out and out.strip().lower().startswith("select schema_name as schema")


def test_rewrite_show_tables_from():
    sql = "SHOW TABLES FROM layerzero_core"
    out = _maybe_rewrite_show_sql(sql)
    assert out and "information_schema.tables" in out and "layerzero_core" in out

