"""Wrapper for extract.query() to avoid FastMCP overload detection.

This module provides a clean interface to extract.query() without exposing
the @overload decorators that FastMCP detects during runtime validation.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Mapping, Sequence

from ..http_client import HttpClient
from .types import Execution, Performance, Query


def execute_query(
    query_or_execution: Query | Execution,
    *,
    verbose: bool = True,
    refresh: bool = False,
    max_age: float | None = None,
    parameters: Mapping[str, Any] | None = None,
    api_key: str | None = None,
    performance: Performance = "medium",
    poll: bool = True,
    poll_interval: float = 1.0,
    timeout_seconds: float | None = None,
    limit: int | None = None,
    offset: int | None = None,
    sample_count: int | None = None,
    sort_by: str | None = None,
    columns: Sequence[str] | None = None,
    extras: Mapping[str, Any] | None = None,
    types: Sequence[type] | Mapping[str, type] | None = None,
    all_types: Sequence[type] | Mapping[str, type] | None = None,
    cache: bool = True,
    cache_dir: str | None = None,
    save_to_cache: bool = True,
    load_from_cache: bool = True,
    include_execution: bool = False,
    http_client: HttpClient | None = None,
) -> Any:
    """
    Execute a Dune query without exposing overloads to FastMCP.
    
    This is a wrapper around extract.query() that has a single, non-overloaded
    signature. FastMCP won't detect overloads when inspecting this function.
    """
    # Import here to avoid FastMCP seeing overloads during module import
    from . import extract
    
    # Call the actual query function - FastMCP won't trace through this wrapper
    try:
        return extract.query(
            query_or_execution=query_or_execution,
            verbose=verbose,
            refresh=refresh,
            max_age=max_age,
            parameters=parameters,
            api_key=api_key,
            performance=performance,
            poll=poll,
            poll_interval=poll_interval,
            timeout_seconds=timeout_seconds,
            limit=limit,
            offset=offset,
            sample_count=sample_count,
            sort_by=sort_by,
            columns=columns,
            extras=extras,
            types=types,
            all_types=all_types,
            cache=cache,
            cache_dir=cache_dir,
            save_to_cache=save_to_cache,
            load_from_cache=load_from_cache,
            include_execution=include_execution,
            http_client=http_client,
        )
    except NotImplementedError as exc:
        # Provide additional context to help diagnose overload issues
        raise RuntimeError(
            "Underlying extract.query() raised NotImplementedError. "
            "This suggests we're calling an overloaded stub."
        ) from exc

