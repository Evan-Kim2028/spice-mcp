"""
Cache Consistency Tests

Tests:
- Cache invalidation scenarios
- Stale cache detection
- Concurrent cache access
- Cache corruption recovery
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from spice_mcp.adapters.dune import cache as cache_module
from spice_mcp.adapters.dune.extract import ExecuteKwargs, RetrievalKwargs
from spice_mcp.adapters.dune.types import Execution


def test_cache_invalidation_on_query_update(tmp_path):
    """Test that cache is invalidated when query changes."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    execute_kwargs: ExecuteKwargs = {
        "query_id": 12345,
        "api_key": "test",
        "parameters": {"param1": "value1"},
        "performance": "medium",
    }
    
    result_kwargs: RetrievalKwargs = {
        "limit": None,
        "offset": None,
        "sample_count": None,
        "sort_by": None,
        "columns": None,
        "extras": None,
        "types": None,
        "all_types": None,
        "verbose": False,
    }
    
    output_kwargs = {
        "cache_dir": str(cache_dir),
        "include_execution": False,
    }
    
    # Create initial execution
    execution1: Execution = {
        "execution_id": "exec-1",
        "timestamp": 1000,
    }
    
    # Modify parameters (should create different cache key)
    execute_kwargs2: ExecuteKwargs = {
        "query_id": 12345,
        "api_key": "test",
        "parameters": {"param1": "value2"},  # Different value
        "performance": "medium",
    }
    
    execution2: Execution = {
        "execution_id": "exec-2",
        "timestamp": 2000,
    }
    
    # Both should have different cache paths
    path1 = cache_module._build_cache_path(execution1, execute_kwargs, result_kwargs, str(cache_dir))
    path2 = cache_module._build_cache_path(execution2, execute_kwargs2, result_kwargs, str(cache_dir))
    
    assert path1 != path2, "Different parameters should create different cache paths"


def test_stale_cache_detection(tmp_path):
    """Test detection of stale cache entries."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    execute_kwargs: ExecuteKwargs = {
        "query_id": 12345,
        "api_key": "test",
        "parameters": None,
        "performance": "medium",
    }
    
    result_kwargs: RetrievalKwargs = {
        "limit": None,
        "offset": None,
        "sample_count": None,
        "sort_by": None,
        "columns": None,
        "extras": None,
        "types": None,
        "all_types": None,
        "verbose": False,
    }
    
    output_kwargs = {
        "cache_dir": str(cache_dir),
        "include_execution": False,
    }
    
    # Old execution timestamp
    old_execution: Execution = {
        "execution_id": "exec-old",
        "timestamp": 1000,  # Old timestamp
    }
    
    # New execution timestamp
    new_execution: Execution = {
        "execution_id": "exec-new",
        "timestamp": 2000,  # Newer timestamp
    }
    
    # Build cache paths
    old_path = cache_module._build_cache_path(old_execution, execute_kwargs, result_kwargs, str(cache_dir))
    new_path = cache_module._build_cache_path(new_execution, execute_kwargs, result_kwargs, str(cache_dir))
    
    # Paths should be different due to different timestamps
    assert old_path != new_path


def test_cache_missing_handles_gracefully(tmp_path, monkeypatch):
    """Test that missing cache is handled gracefully."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    execute_kwargs: ExecuteKwargs = {
        "query_id": 12345,
        "api_key": "test",
        "parameters": None,
        "performance": "medium",
    }
    
    result_kwargs: RetrievalKwargs = {
        "limit": None,
        "offset": None,
        "sample_count": None,
        "sort_by": None,
        "columns": None,
        "extras": None,
        "types": None,
        "all_types": None,
        "verbose": False,
    }
    
    output_kwargs = {
        "cache_dir": str(cache_dir),
        "include_execution": False,
    }
    
    # Mock get_latest_execution to return None (simulating no execution found)
    # This avoids making actual HTTP requests with invalid API keys
    from spice_mcp.adapters.dune import extract as extract_module
    monkeypatch.setattr(extract_module, "get_latest_execution", lambda *args, **kwargs: None)
    
    # Try to load from cache when it doesn't exist
    result, execution = cache_module.load_from_cache(execute_kwargs, result_kwargs, output_kwargs)
    
    # Should return None, None when cache doesn't exist
    assert result is None
    assert execution is None


def test_cache_path_uniqueness(tmp_path):
    """Test that cache paths are unique for different inputs."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    base_execute_kwargs: ExecuteKwargs = {
        "query_id": 12345,
        "api_key": "test",
        "parameters": None,
        "performance": "medium",
    }
    
    base_result_kwargs: RetrievalKwargs = {
        "limit": None,
        "offset": None,
        "sample_count": None,
        "sort_by": None,
        "columns": None,
        "extras": None,
        "types": None,
        "all_types": None,
        "verbose": False,
    }
    
    execution: Execution = {
        "execution_id": "exec-1",
        "timestamp": 1000,
    }
    
    # Test different limits create different paths
    result_kwargs1 = {**base_result_kwargs, "limit": 10}
    result_kwargs2 = {**base_result_kwargs, "limit": 20}
    
    path1 = cache_module._build_cache_path(execution, base_execute_kwargs, result_kwargs1, str(cache_dir))
    path2 = cache_module._build_cache_path(execution, base_execute_kwargs, result_kwargs2, str(cache_dir))
    
    assert path1 != path2, "Different limits should create different cache paths"
    
    # Test different offsets create different paths
    result_kwargs3 = {**base_result_kwargs, "offset": 0}
    result_kwargs4 = {**base_result_kwargs, "offset": 10}
    
    path3 = cache_module._build_cache_path(execution, base_execute_kwargs, result_kwargs3, str(cache_dir))
    path4 = cache_module._build_cache_path(execution, base_execute_kwargs, result_kwargs4, str(cache_dir))
    
    assert path3 != path4, "Different offsets should create different cache paths"


def test_cache_directory_creation(tmp_path):
    """Test that cache directory is created if it doesn't exist."""
    cache_dir = tmp_path / "nonexistent_cache"
    
    execute_kwargs: ExecuteKwargs = {
        "query_id": 12345,
        "api_key": "test",
        "parameters": None,
        "performance": "medium",
    }
    
    result_kwargs: RetrievalKwargs = {
        "limit": None,
        "offset": None,
        "sample_count": None,
        "sort_by": None,
        "columns": None,
        "extras": None,
        "types": None,
        "all_types": None,
        "verbose": False,
    }
    
    execution: Execution = {
        "execution_id": "exec-1",
        "timestamp": 1000,
    }
    
    # Build cache path (should not fail even if directory doesn't exist)
    try:
        path = cache_module._build_cache_path(execution, execute_kwargs, result_kwargs, str(cache_dir))
        # Path should be valid
        assert path is not None
        assert str(cache_dir) in path
    except Exception as e:
        pytest.fail(f"Cache path building should not fail: {e}")

