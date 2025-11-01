"""
Tests for dbt config parsing and verification features.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from spice_mcp.adapters.spellbook.explorer import SpellbookExplorer
from spice_mcp.service_layer.verification_service import VerificationService


def test_parse_dbt_config_with_schema_and_alias(tmp_path):
    """Test parsing dbt config with schema and alias."""
    sql_file = tmp_path / "test_model.sql"
    sql_content = """
{{ config(
    schema='sui_walrus',
    alias='base_table',
    materialized='table'
) }}

SELECT * FROM source_table
"""
    sql_file.write_text(sql_content)
    
    explorer = SpellbookExplorer(repo_path=tmp_path)
    config = explorer._parse_dbt_config(sql_file)
    
    assert config["schema"] == "sui_walrus"
    assert config["alias"] == "base_table"


def test_parse_dbt_config_with_double_quotes(tmp_path):
    """Test parsing dbt config with double quotes."""
    sql_file = tmp_path / "test_model.sql"
    sql_content = """
{{ config(
    schema="layerzero",
    alias="send"
) }}

SELECT * FROM source_table
"""
    sql_file.write_text(sql_content)
    
    explorer = SpellbookExplorer(repo_path=tmp_path)
    config = explorer._parse_dbt_config(sql_file)
    
    assert config["schema"] == "layerzero"
    assert config["alias"] == "send"


def test_parse_dbt_config_without_config(tmp_path):
    """Test parsing SQL file without dbt config."""
    sql_file = tmp_path / "test_model.sql"
    sql_content = """
SELECT * FROM source_table
"""
    sql_file.write_text(sql_content)
    
    explorer = SpellbookExplorer(repo_path=tmp_path)
    config = explorer._parse_dbt_config(sql_file)
    
    assert config == {}


def test_parse_dbt_config_only_schema(tmp_path):
    """Test parsing dbt config with only schema."""
    sql_file = tmp_path / "test_model.sql"
    sql_content = """
{{ config(schema='test_schema') }}
SELECT * FROM source_table
"""
    sql_file.write_text(sql_content)
    
    explorer = SpellbookExplorer(repo_path=tmp_path)
    config = explorer._parse_dbt_config(sql_file)
    
    assert config["schema"] == "test_schema"
    assert "alias" not in config


def test_verification_service_cache(tmp_path):
    """Test verification service caching."""
    cache_path = tmp_path / "cache.json"
    mock_adapter = MagicMock()
    
    # Mock describe_table to return successfully (table exists)
    mock_adapter.describe_table.return_value = MagicMock()
    
    service = VerificationService(cache_path=cache_path, dune_adapter=mock_adapter)
    
    # Verify table (should query Dune)
    result = service.verify_tables_batch([("sui_walrus", "base_table")])
    assert result["sui_walrus.base_table"] is True
    assert mock_adapter.describe_table.called
    
    # Reset mock
    mock_adapter.describe_table.reset_mock()
    
    # Verify again (should use cache, not query Dune)
    result = service.verify_tables_batch([("sui_walrus", "base_table")])
    assert result["sui_walrus.base_table"] is True
    assert not mock_adapter.describe_table.called  # Should use cache


def test_verification_service_non_existent_table(tmp_path):
    """Test verification service with non-existent table."""
    cache_path = tmp_path / "cache.json"
    mock_adapter = MagicMock()
    
    # Mock describe_table to raise exception (table doesn't exist)
    mock_adapter.describe_table.side_effect = Exception("Table not found")
    
    service = VerificationService(cache_path=cache_path, dune_adapter=mock_adapter)
    
    # Verify table (should return False)
    result = service.verify_tables_batch([("nonexistent", "table")])
    assert result["nonexistent.table"] is False


def test_verification_service_batch_verification(tmp_path):
    """Test verification service batch verification."""
    cache_path = tmp_path / "cache.json"
    mock_adapter = MagicMock()
    
    # Mock describe_table to return successfully
    mock_adapter.describe_table.return_value = MagicMock()
    
    service = VerificationService(cache_path=cache_path, dune_adapter=mock_adapter)
    
    # Verify multiple tables
    tables = [
        ("sui_walrus", "base_table"),
        ("layerzero", "send"),
        ("dex", "trades"),
    ]
    result = service.verify_tables_batch(tables)
    
    assert len(result) == 3
    assert all(result.values())  # All should be True
    assert mock_adapter.describe_table.call_count == 3


def test_verification_service_persistent_cache(tmp_path):
    """Test that verification cache persists across service instances."""
    cache_path = tmp_path / "cache.json"
    mock_adapter = MagicMock()
    mock_adapter.describe_table.return_value = MagicMock()
    
    # First service instance
    service1 = VerificationService(cache_path=cache_path, dune_adapter=mock_adapter)
    service1.verify_tables_batch([("test", "table")])
    
    # Verify cache file exists
    assert cache_path.exists()
    
    # Second service instance (should load cache)
    mock_adapter2 = MagicMock()
    service2 = VerificationService(cache_path=cache_path, dune_adapter=mock_adapter2)
    
    # Verify table (should use cache, not query)
    result = service2.verify_tables_batch([("test", "table")])
    assert result["test.table"] is True
    assert not mock_adapter2.describe_table.called  # Should use cache

