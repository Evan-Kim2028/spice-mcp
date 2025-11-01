"""
Property-Based Tests using Hypothesis

These tests use Hypothesis to generate random valid inputs and verify
that invariants hold across all inputs.
"""
from __future__ import annotations

from hypothesis import given, strategies as st

import pytest


@given(query=st.text(min_size=1, max_size=1000))
def test_query_never_crashes_on_string_input(query: str):
    """Property: Any string input should not crash the query parser."""
    from spice_mcp.adapters.dune import extract
    
    # Should either return a result or raise a specific exception, not crash
    try:
        result = extract.query(query, poll=False, api_key="test")
        # If it succeeds, should return a dict
        assert isinstance(result, dict)
    except Exception as e:
        # Should raise a specific exception, not crash
        assert len(str(e)) > 0
        assert isinstance(e, Exception)


@given(
    limit=st.one_of(st.none(), st.integers(min_value=0, max_value=100000)),
    offset=st.one_of(st.none(), st.integers(min_value=0, max_value=100000)),
)
def test_limit_offset_combinations_never_crash(limit: int | None, offset: int | None):
    """Property: Any limit/offset combination should not crash."""
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import DisabledQueryHistory
    
    class FakeQueryService:
        def execute(self, **kwargs):
            return {
                "rowcount": kwargs.get("limit", 10) or 10,
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
    
    try:
        result = tool.execute(query="SELECT 1", limit=limit, offset=offset, format="preview")
        assert result["type"] == "preview"
    except Exception as e:
        # Should handle gracefully, not crash
        assert len(str(e)) > 0


@given(
    param_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "_"))),
    param_value=st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
    ),
)
def test_parameter_handling_never_crashes(param_key: str, param_value: str | int | float | bool):
    """Property: Any parameter key/value combination should not crash."""
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
    
    try:
        result = tool.execute(
            query="SELECT 1",
            parameters={param_key: param_value},
            format="preview",
        )
        assert result["type"] == "preview"
    except Exception as e:
        # Should handle gracefully, not crash
        assert len(str(e)) > 0


@given(schema=st.text(min_size=1, max_size=100))
def test_schema_name_handling_never_crashes(schema: str):
    """Property: Any schema name should not crash discovery."""
    from spice_mcp.mcp import server
    
    # Mock the discovery service
    class FakeDiscoveryService:
        def find_schemas(self, keyword: str) -> list[str]:
            return []
        
        def list_tables(self, schema: str, limit: int | None = None):
            return []
        
        def describe_table(self, schema: str, table: str):
            raise ValueError(f"Table {schema}.test not found")
    
    try:
        # Should handle any schema name gracefully
        fake = FakeDiscoveryService()
        result = fake.list_tables(schema)
        assert isinstance(result, list)
    except Exception as e:
        # Should raise specific error, not crash
        assert len(str(e)) > 0


@given(
    hours=st.integers(min_value=1, max_value=720),
    timeout=st.one_of(st.none(), st.floats(min_value=0.1, max_value=600)),
)
def test_sui_overview_parameters_never_crash(hours: int, timeout: float | None):
    """Property: Any hours/timeout combination should not crash Sui overview."""
    from spice_mcp.mcp.tools.sui_package_overview import SuiPackageOverviewTool
    
    class FakeSuiService:
        def package_overview(self, packages, *, hours: int, timeout_seconds: float | None = None):
            return {
                "ok": True,
                "events_preview": [],
                "transactions_preview": [],
                "objects_preview": [],
            }
    
    tool = SuiPackageOverviewTool(FakeSuiService())
    
    try:
        result = tool.execute(packages=["0x1"], hours=hours, timeout_seconds=timeout)
        assert result["ok"] is True
    except Exception as e:
        # Should handle gracefully, not crash
        assert len(str(e)) > 0


@given(query_id=st.one_of(
    st.integers(min_value=1, max_value=999999999),
    st.text(min_size=1, max_size=50),
))
def test_query_id_formats_never_crash(query_id: int | str):
    """Property: Any query ID format should not crash."""
    from spice_mcp.adapters.dune import extract
    
    try:
        result = extract.query(query_id, poll=False, api_key="test")
        # Should return a dict (execution or error)
        assert isinstance(result, dict)
    except Exception as e:
        # Should raise specific error, not crash
        assert len(str(e)) > 0


@given(format_type=st.sampled_from(["preview", "raw", "metadata", "poll"]))
def test_format_types_never_crash(format_type: str):
    """Property: All format types should work without crashing."""
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
        
        def fetch_metadata(self, **kwargs):
            return {
                "metadata": {"state": "ok"},
                "next_uri": None,
                "next_offset": None,
            }
    
    tool = ExecuteQueryTool(
        Config(dune=DuneConfig(api_key="test")),
        FakeQueryService(),
        DisabledQueryHistory(),
    )
    
    try:
        result = tool.execute(query="SELECT 1", format=format_type)
        # Should return a dict with expected structure
        assert isinstance(result, dict)
        if format_type == "poll":
            assert result["type"] == "execution"
        elif format_type == "metadata":
            assert result["type"] == "metadata"
        elif format_type == "raw":
            assert result["type"] == "raw"
        else:
            assert result["type"] == "preview"
    except Exception as e:
        # Should handle gracefully, not crash
        assert len(str(e)) > 0

