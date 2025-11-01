"""Tests for typing utilities, especially environment variable handling."""

from __future__ import annotations

import os
from unittest.mock import patch

from spice_mcp.adapters.dune.typing_utils import resolve_raw_sql_template_id


def test_resolve_raw_sql_template_id_default():
    """Test that the function returns the default template ID when no env var is set."""
    # Ensure env var is not set
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_raw_sql_template_id()
        assert result == 4060379
        assert isinstance(result, int)


def test_resolve_raw_sql_template_id_from_env():
    """Test that the function reads from the SPICE_RAW_SQL_QUERY_ID environment variable."""
    custom_id = "12345"
    with patch.dict(os.environ, {"SPICE_RAW_SQL_QUERY_ID": custom_id}):
        result = resolve_raw_sql_template_id()
        assert result == int(custom_id)


def test_resolve_raw_sql_template_id_invalid_env():
    """Test that the function handles invalid environment variable values gracefully."""
    with patch.dict(os.environ, {"SPICE_RAW_SQL_QUERY_ID": "invalid_number"}):
        # Function should gracefully fallback to default when conversion fails
        result = resolve_raw_sql_template_id()
        assert result == 4060379  # Should fallback to default
        assert isinstance(result, int)


def test_resolve_raw_sql_template_id_zero_env():
    """Test that the function handles zero value correctly."""
    with patch.dict(os.environ, {"SPICE_RAW_SQL_QUERY_ID": "0"}):
        result = resolve_raw_sql_template_id()
        assert result == 0


def test_determine_input_type_raw_sql_uses_template_id(monkeypatch):
    """Test that determine_input_type correctly resolves raw SQL using the template ID."""
    from spice_mcp.adapters.dune.extract import determine_input_type
    
    # Test with default template ID
    with patch.dict(os.environ, {}, clear=True):
        query_id, execution, parameters = determine_input_type("SELECT 1 as test")
        assert query_id == 4060379
        assert execution is None
        assert parameters == {"query": "SELECT 1 as test"}
    
    # Test with custom template ID
    with patch.dict(os.environ, {"SPICE_RAW_SQL_QUERY_ID": "12345"}):
        query_id, execution, parameters = determine_input_type("SELECT count(*) as total")
        assert query_id == 12345
        assert execution is None
        assert parameters == {"query": "SELECT count(*) as total"}
