from __future__ import annotations

import os
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

import polars as pl

from ...config import Config
from ...core.models import (
    QueryRequest,
    QueryResult,
    ResultMetadata,
    ResultPreview,
    SchemaMatch,
    TableColumn,
    TableDescription,
    TableSummary,
)
from ...core.ports import CatalogExplorer, QueryExecutor
from ...polars_utils import collect_preview
from ..http_client import HttpClient, HttpClientConfig
from . import urls

# Use wrapper to avoid FastMCP detecting overloads in extract.query()
from .query_wrapper import execute_query as _execute_dune_query


class DuneAdapter(QueryExecutor, CatalogExplorer):
    """Thin façade around the vendored extract module."""

    def __init__(
        self,
        config: Config,
        *,
        http_client: HttpClient | None = None,
    ):
        self.config = config
        http_config: HttpClientConfig = config.http
        self._http = http_client or HttpClient(http_config)

    # QueryExecutor -----------------------------------------------------------------
    def execute(self, request: QueryRequest) -> QueryResult:
        self._ensure_api_key()
        start = time.time()
        q = request.query
        if isinstance(q, str):
            q_rewritten = _maybe_rewrite_show_sql(q)
            if q_rewritten is not None:
                q = q_rewritten
        result = _execute_dune_query(
            query_or_execution=q,
            verbose=False,
            refresh=request.refresh,
            max_age=request.max_age,
            parameters=request.parameters,
            api_key=self._api_key(),
            performance=request.performance or "medium",
            poll=request.poll,
            timeout_seconds=request.timeout_seconds,
            limit=request.limit,
            offset=request.offset,
            sample_count=request.sample_count,
            sort_by=request.sort_by,
            columns=request.columns,
            cache_dir=self.config.cache.cache_dir,
            include_execution=request.include_execution,
            http_client=self._http,
        )
        if request.include_execution:
            df, execution = result
        else:
            df = result
            execution = {}
        duration_ms = int((time.time() - start) * 1000)
        columns = list(df.columns)
        rowcount = int(len(df))
        lazyframe = df.lazy()
        preview = _build_preview(lazyframe, columns, rowcount)
        del df
        # Use rewritten SQL for metadata determination too
        req_for_meta = request
        try:
            from dataclasses import replace

            if isinstance(q, str) and q != request.query:
                req_for_meta = replace(request, query=q)  # type: ignore[arg-type]
        except Exception:
            pass
        meta = self.fetch_metadata(req_for_meta, execution=execution)
        meta.duration_ms = duration_ms
        return QueryResult(preview=preview, info=meta, lazyframe=lazyframe)

    def fetch_metadata(
        self, request: QueryRequest, *, execution: Mapping[str, Any] | None = None
    ) -> ResultMetadata:
        self._ensure_api_key()
        query_id, _, effective_params = extract._determine_input_type(  # type: ignore[attr-defined]
            request.query,
            request.parameters,
        )

        payload: dict[str, Any] = {}
        next_uri: str | None = None
        next_offset: int | None = None

        if query_id is not None:
            params: dict[str, Any] = {}
            if effective_params is not None:
                params["query_parameters"] = effective_params
            params.update(
                {
                    "limit": request.limit,
                    "offset": request.offset,
                    "sample_count": request.sample_count,
                    "sort_by": request.sort_by,
                    "columns": list(request.columns) if request.columns else None,
                }
            )
            if request.extras:
                try:
                    params.update(request.extras)
                except Exception:
                    pass

            url = urls.get_query_results_url(query_id, parameters=params, csv=False)
            from .user_agent import get_user_agent
            headers = {
                "X-Dune-API-Key": self._api_key(),
                "User-Agent": get_user_agent(),
            }
            try:
                resp = self._http.request("GET", url, headers=headers)
                data = resp.json()
                if isinstance(data, dict):
                    payload = data.get("result", {}).get("metadata") or {}
                    next_uri = data.get("next_uri")
                    next_offset = data.get("next_offset")
                    if "error" in data:
                        payload = {**payload, "error": data["error"]}
                    if "state" in data:
                        payload = {**payload, "state": data["state"]}
            except Exception:
                payload = {}

        execution_meta: dict[str, Any] = {}
        if execution:
            execution_meta = dict(execution)

        return ResultMetadata(
            execution=execution_meta,
            duration_ms=0,
            metadata=payload or None,
            next_offset=next_offset,
            next_uri=next_uri,
        )

    # CatalogExplorer ---------------------------------------------------------------
    def find_schemas(self, keyword: str) -> Sequence[SchemaMatch]:
        sql = f"SHOW SCHEMAS LIKE '%{keyword}%'"
        df = self._run_sql(sql)
        return [SchemaMatch(schema=row.get("Schema", "")) for row in df.to_dicts()]

    def list_tables(self, schema: str, limit: int | None = None) -> Sequence[TableSummary]:
        sql = f"SHOW TABLES FROM {schema}"
        df = self._run_sql(sql, limit=limit)
        return [
            TableSummary(schema=schema, table=row.get("Table", row.get("name", "")))
            for row in df.to_dicts()
        ]

    def describe_table(self, schema: str, table: str) -> TableDescription:
        fq = f"{schema}.{table}"

        try:
            df = self._run_sql(f"SHOW COLUMNS FROM {fq}")
            rows = df.to_dicts()
            columns = [
                TableColumn(
                    name=row.get("Column") or row.get("column_name") or "",
                    dune_type=row.get("Type") or row.get("data_type"),
                    polars_dtype=row.get("Type") or None,
                    comment=row.get("Comment"),
                    extra=row.get("Extra"),
                )
                for row in rows
            ]
            return TableDescription(fully_qualified_name=fq, columns=columns)
        except Exception:
            df = self._run_sql(f"SELECT * FROM {fq} LIMIT 1")
            columns = [
                TableColumn(name=name, polars_dtype=str(dtype))
                for name, dtype in zip(df.columns, df.dtypes)
            ]
            return TableDescription(fully_qualified_name=fq, columns=columns)

    # Internal helpers --------------------------------------------------------------
    def _run_sql(self, sql: str, *, limit: int | None = None) -> pl.DataFrame:
        self._ensure_api_key()
        sql_eff = _maybe_rewrite_show_sql(sql) or sql
        df = _execute_dune_query(
            query_or_execution=sql_eff,
            verbose=False,
            performance="medium",
            timeout_seconds=self.config.default_timeout_seconds,
            limit=limit,
            cache_dir=self.config.cache.cache_dir,
            http_client=self._http,
        )
        if limit is not None and len(df) > limit:
            return df.head(limit)
        return df

    def _ensure_api_key(self) -> None:
        if not os.getenv("DUNE_API_KEY"):
            os.environ["DUNE_API_KEY"] = self._api_key()

    def _api_key(self) -> str:
        return self.config.dune.api_key


def _build_preview(lf: pl.LazyFrame, columns: list[str], rowcount: int) -> ResultPreview:
    preview_rows = min(10, rowcount)
    data_preview = collect_preview(lf, preview_rows)
    return ResultPreview(
        rowcount=rowcount,
        columns=columns,
        data_preview=data_preview,
    )


def _maybe_rewrite_show_sql(sql: str) -> str | None:
    """Rewrite certain SHOW statements to information_schema SELECTs for portability.

    This allows running discovery-style commands through the parameterized raw SQL
    template which expects SELECT statements.
    """
    s = sql.strip()
    m = re.match(r"^SHOW\s+SCHEMAS\s+LIKE\s+'([^']+)'\s*;?$", s, flags=re.IGNORECASE)
    if m:
        pat = m.group(1)
        return (
            "SELECT schema_name AS Schema FROM information_schema.schemata "
            f"WHERE schema_name LIKE '{pat}'"
        )
    if re.match(r"^SHOW\s+SCHEMAS\s*;?$", s, flags=re.IGNORECASE):
        return "SELECT schema_name AS Schema FROM information_schema.schemata"

    m = re.match(r"^SHOW\s+TABLES\s+FROM\s+([A-Za-z0-9_\.]+)\s*;?$", s, flags=re.IGNORECASE)
    if m:
        schema = m.group(1)
        return (
            "SELECT table_name AS Table FROM information_schema.tables "
            f"WHERE table_schema = '{schema}'"
        )

    return None
