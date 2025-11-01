from __future__ import annotations

from typing import Any

from ..core.models import QueryRequest
from ..core.ports import QueryExecutor
from ..polars_utils import collect_all


class QueryService:
    """Service layer orchestrating query execution via the Dune adapter."""

    def __init__(self, executor: QueryExecutor):
        self.executor = executor

    def execute(
        self,
        query: int | str,
        *,
        parameters: dict[str, Any] | None = None,
        refresh: bool = False,
        max_age: float | None = None,
        poll: bool = True,
        timeout_seconds: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sample_count: int | None = None,
        sort_by: str | None = None,
        columns: list[str] | None = None,
        extras: dict[str, Any] | None = None,
        include_execution: bool = True,
        performance: str | None = None,
        return_raw: bool = False,
    ) -> dict[str, Any]:
        """Execute a Dune query and return the normalized payload for MCP tools."""
        request = QueryRequest(
            query=query,
            parameters=parameters,
            refresh=refresh,
            max_age=max_age,
            poll=poll,
            timeout_seconds=timeout_seconds,
            limit=limit,
            offset=offset,
            sample_count=sample_count,
            sort_by=sort_by,
            columns=columns,
            extras=extras,
            include_execution=include_execution,
            performance=performance,
        )

        result = self.executor.execute(request)
        lazyframe = getattr(result, "lazyframe", None)

        payload: dict[str, Any] = {
            "rowcount": result.preview.rowcount,
            "columns": result.preview.columns,
            "data_preview": result.preview.data_preview,
            "execution": result.info.execution,
            "duration_ms": result.info.duration_ms,
        }

        if return_raw:
            if lazyframe is not None:
                payload["data"] = collect_all(lazyframe)
            else:
                payload["data"] = result.preview.data_preview

        if result.info.metadata is not None:
            payload["metadata"] = result.info.metadata
        if result.info.next_offset is not None:
            payload["next_offset"] = result.info.next_offset
        if result.info.next_uri is not None:
            payload["next_uri"] = result.info.next_uri

        return payload

    def fetch_metadata(
        self,
        query: int | str,
        *,
        parameters: dict[str, Any] | None = None,
        max_age: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sample_count: int | None = None,
        sort_by: str | None = None,
        columns: list[str] | None = None,
        extras: dict[str, Any] | None = None,
        performance: str | None = None,
    ) -> dict[str, Any]:
        """Fetch metadata for a query without materializing rows."""
        request = QueryRequest(
            query=query,
            parameters=parameters,
            max_age=max_age,
            poll=False,
            limit=limit,
            offset=offset,
            sample_count=sample_count,
            sort_by=sort_by,
            columns=columns,
            extras=extras,
            performance=performance,
        )
        meta = self.executor.fetch_metadata(request)
        payload: dict[str, Any] = {
            "execution": meta.execution,
            "duration_ms": meta.duration_ms,
        }
        if meta.metadata is not None:
            payload["metadata"] = meta.metadata
        if meta.next_offset is not None:
            payload["next_offset"] = meta.next_offset
        if meta.next_uri is not None:
            payload["next_uri"] = meta.next_uri
        return payload
