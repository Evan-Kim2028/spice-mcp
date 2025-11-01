from __future__ import annotations

from pathlib import Path

import polars as pl

from spice_mcp.adapters.dune import cache


def _make_df():
    return pl.DataFrame({"a": [1, 2, 3]})


def test_build_cache_path_hash_determinism(tmp_path, monkeypatch):
    exec_obj = {"execution_id": "exe-1", "timestamp": 1700000000}

    execute_kwargs = {
        "query_id": 42,
        "api_key": None,
        "parameters": {"x": 1, "y": 2},
        "performance": "medium",
    }
    result_kwargs_a = {
        "limit": 10,
        "offset": 0,
        "sample_count": None,
        "sort_by": None,
        "columns": None,
        "extras": None,
        "types": None,
        "all_types": None,
        "verbose": False,
    }
    # Same dict content but different key order
    result_kwargs_b = dict(reversed(list(result_kwargs_a.items())))

    p1 = cache._build_cache_path(
        exec_obj, execute_kwargs, result_kwargs_a, str(tmp_path)
    )
    p2 = cache._build_cache_path(
        exec_obj, execute_kwargs, result_kwargs_b, str(tmp_path)
    )
    assert p1 == p2


def test_save_and_load_from_cache_roundtrip(tmp_path, monkeypatch):
    # Patch latest execution resolution to avoid network
    from spice_mcp.adapters.dune import extract

    exec_obj = {"execution_id": "exe-2", "timestamp": 1700001234}
    monkeypatch.setattr(extract, "get_latest_execution", lambda *_args, **_kw: exec_obj)

    execute_kwargs = {
        "query_id": 77,
        "api_key": None,
        "parameters": None,
        "performance": "medium",
    }
    result_kwargs = {
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
        "execute_kwargs": execute_kwargs,
        "result_kwargs": result_kwargs,
        "cache": True,
        "save_to_cache": True,
        "cache_dir": str(tmp_path),
        "include_execution": False,
    }

    df = _make_df()
    cache.save_to_cache(df, exec_obj, execute_kwargs, result_kwargs, str(tmp_path))

    loaded, returned_exec = cache.load_from_cache(
        execute_kwargs, result_kwargs, output_kwargs
    )
    assert isinstance(loaded, pl.DataFrame)
    assert returned_exec == exec_obj
    assert loaded.shape == df.shape


def test_load_from_cache_includes_execution_when_requested(tmp_path, monkeypatch):
    from spice_mcp.adapters.dune import extract

    exec_obj = {"execution_id": "exe-3", "timestamp": 1700005678}
    monkeypatch.setattr(extract, "get_latest_execution", lambda *_args, **_kw: exec_obj)

    execute_kwargs = {
        "query_id": 88,
        "api_key": None,
        "parameters": None,
        "performance": "medium",
    }
    result_kwargs = {
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
        "execute_kwargs": execute_kwargs,
        "result_kwargs": result_kwargs,
        "cache": True,
        "save_to_cache": True,
        "cache_dir": str(tmp_path),
        "include_execution": True,
    }

    path = cache._build_cache_path(exec_obj, execute_kwargs, result_kwargs, str(tmp_path))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({"a": [1]}).write_parquet(path)

    loaded, returned_exec = cache.load_from_cache(execute_kwargs, result_kwargs, output_kwargs)

    assert isinstance(loaded, tuple)
    df_loaded, exec_meta = loaded
    assert exec_meta == exec_obj
    assert returned_exec == exec_obj
    assert df_loaded.shape == (1, 1)
