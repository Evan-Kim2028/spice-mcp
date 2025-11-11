from __future__ import annotations

import os
import time
from typing import Any

from ...adapters.dune import urls as dune_urls
from ...adapters.dune.query_wrapper import execute_query as execute_dune_query

# Import user_agent from separate module to avoid importing overloaded functions
from ...adapters.dune.user_agent import get_user_agent as get_dune_user_agent
from ...adapters.http_client import HttpClient
from ...config import Config
from ...core.errors import error_response
from ...logging.query_history import QueryHistory
from ...service_layer.query_service import QueryService
from .base import MCPTool


class ExecuteQueryTool(MCPTool):
    """MCP tool for executing Dune Analytics queries."""

    def __init__(
        self,
        config: Config,
        query_service: QueryService,
        query_history: QueryHistory,
    ):
        self.config = config
        self.query_service = query_service
        self.query_history = query_history
        self._http = HttpClient(config.http)

    @property
    def name(self) -> str:
        return "dune_query"

    @property
    def description(self) -> str:
        return (
            "Execute Dune Analytics queries (by ID, URL, or raw SQL) and return "
            "agent-optimized results with a compact preview."
        )

    def get_parameter_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query ID, URL, or raw SQL"},
                "parameters": {"type": "object", "description": "Query parameters"},
                "refresh": {"type": "boolean", "default": False},
                "max_age": {"type": "number"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
                "sample_count": {"type": "integer"},
                "sort_by": {"type": "string"},
                "columns": {"type": "array", "items": {"type": "string"}},
                "performance": {
                    "type": "string",
                    "enum": ["medium", "large"],
                    "default": "medium",
                    "description": "Request the medium (default) or large performance tier.",
                },
                "format": {
                    "type": "string",
                    "enum": ["preview", "raw", "metadata", "poll"],
                    "default": "preview",
                    "description": "Preview returns compact data; raw returns all rows; poll returns execution handle only",
                },
                "extras": {
                    "type": "object",
                    "description": "Optional advanced flags passed through to results (e.g., allow_partial_results)",
                    "additionalProperties": True,
                    "properties": {
                        "allow_partial_results": {"type": "boolean"},
                        "ignore_max_datapoints_per_request": {"type": "boolean"},
                    },
                },
                "timeout_seconds": {"type": "number", "description": "Polling timeout in seconds"},
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def execute(
        self,
        *,
        query: str,
        parameters: dict[str, Any] | None = None,
        refresh: bool = False,
        max_age: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sample_count: int | None = None,
        sort_by: str | None = None,
        columns: list[str] | None = None,
        performance: str = "medium",
        format: str = "preview",
        extras: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        t0 = time.time()
        try:
            # Use native SHOW statements directly - they're faster than information_schema queries
            # See issue #10: https://github.com/Evan-Kim2028/spice-mcp/issues/10
            # Removed rewrite to avoid performance issues with information_schema queries
            q_use = query
            # Poll-only: return execution handle without fetching results
            if format == "poll":
                exec_obj = execute_dune_query(
                    q_use,
                    parameters=parameters,
                    api_key=self.config.dune.api_key,
                    performance=performance,
                    poll=False,
                    http_client=self._http,
                )
                execution_id = exec_obj.get("execution_id", "unknown")

                q_type = _categorize_query(q_use)
                q_sha = self._persist_query_sql(q_use, q_type)

                # Determine IDs for history
                q_id_value = None
                template_id_value = None
                raw_sql_engine = os.getenv("SPICE_DUNE_RAW_SQL_ENGINE", "execution_sql")
                try:
                    if q_type == "query_id":
                        q_id_value = int(q_use)
                    elif q_type == "url":
                        q_id_value = dune_urls.get_query_id(q_use)
                    else:
                        # raw SQL: only use template id if using template engine
                        if raw_sql_engine == "template":
                            template_id_value = int(os.getenv("SPICE_RAW_SQL_QUERY_ID", "4060379"))
                except Exception:
                    pass

                extra_fields: dict[str, Any] = {}
                if q_id_value is not None:
                    extra_fields["query_id"] = q_id_value
                if template_id_value is not None:
                    extra_fields["template_query_id"] = template_id_value

                self.query_history.record(
                    execution_id=execution_id,
                    query_type=q_type,
                    query_preview=query,
                    status="submitted",
                    duration_ms=int((time.time() - t0) * 1000),
                    query_sha256=q_sha,
                    cache_hit=False,
                    **extra_fields,
                )
                return {"type": "execution", "execution_id": execution_id, "status": "submitted"}

            if format == "metadata":
                meta = self.query_service.fetch_metadata(
                    query=q_use,
                    parameters=parameters,
                    max_age=max_age,
                    limit=limit,
                    offset=offset,
                    sample_count=sample_count,
                    sort_by=sort_by,
                    columns=columns,
                    extras=extras,
                    performance=performance,
                )
                return {
                    "type": "metadata",
                    "metadata": meta.get("metadata"),
                    "next_uri": meta.get("next_uri"),
                    "next_offset": meta.get("next_offset"),
                }
            result = self.query_service.execute(
                query=q_use,
                parameters=parameters,
                refresh=refresh,
                max_age=max_age,
                poll=True,
                timeout_seconds=timeout_seconds,
                limit=limit,
                offset=offset,
                sample_count=sample_count,
                sort_by=sort_by,
                columns=columns,
                extras=extras,
                include_execution=True,
                performance=performance,
                return_raw=format == "raw",
            )

            duration_ms = int((time.time() - t0) * 1000)
            execution = result.get("execution", {})
            execution_id = execution.get("execution_id", "unknown")

            q_type = _categorize_query(q_use)
            q_sha = self._persist_query_sql(q_use, q_type)

            # Determine query id (or template id for raw SQL) for history
            q_id_value: int | None = None
            template_id_value: int | None = None
            raw_sql_engine = os.getenv("SPICE_DUNE_RAW_SQL_ENGINE", "execution_sql")
            try:
                if q_type == "query_id":
                    q_id_value = int(q_use)
                elif q_type == "url":
                    q_id_value = dune_urls.get_query_id(q_use)
                else:
                    # raw SQL: only use template id if using template engine
                    if raw_sql_engine == "template":
                        tmpl = os.getenv("SPICE_RAW_SQL_QUERY_ID", "4060379")
                        template_id_value = int(tmpl)
            except Exception:
                pass

            extra_fields: dict[str, Any] = {}
            if q_id_value is not None:
                extra_fields["query_id"] = q_id_value
            if template_id_value is not None:
                extra_fields["template_query_id"] = template_id_value

            self.query_history.record(
                execution_id=execution_id,
                query_type=q_type,
                query_preview=query,
                status="success",
                duration_ms=duration_ms,
                rowcount=result.get("rowcount"),
                query_sha256=q_sha,
                cache_hit=False,
                **extra_fields,
            )

            # Derive ids for payload and history
            q_id_value = None
            template_id_value = None
            raw_sql_engine = os.getenv("SPICE_DUNE_RAW_SQL_ENGINE", "execution_sql")
            try:
                if q_type == "query_id":
                    q_id_value = int(query)
                elif q_type == "url":
                    q_id_value = dune_urls.get_query_id(query)
                else:
                    # raw SQL: only use template id if using template engine
                    if raw_sql_engine == "template":
                        template_id_value = int(os.getenv("SPICE_RAW_SQL_QUERY_ID", "4060379"))
            except Exception:
                pass

            payload = {**result}
            payload["execution_id"] = execution_id
            payload["duration_ms"] = result.get("duration_ms") if result.get("duration_ms") is not None else duration_ms
            if q_id_value is not None:
                payload["query_id"] = q_id_value
            if template_id_value is not None:
                payload["template_query_id"] = template_id_value
            # User-friendly web URL for the query (or template for raw SQL)
            q_for_url = q_id_value if q_id_value is not None else template_id_value
            if q_for_url is not None:
                payload["query_url"] = f"https://dune.com/queries/{q_for_url}"
            if "metadata" not in payload:
                payload["metadata"] = None
            if format == "raw":
                payload["type"] = "raw"
                payload["data"] = result.get("data") or result.get("data_preview")
            else:
                payload["type"] = "preview"
            return payload
        except Exception as exc:
            duration_ms = int((time.time() - t0) * 1000)
            # Try to include query id info on error as well
            q_type = _categorize_query(q_use)
            q_id_value: int | None = None
            template_id_value: int | None = None
            raw_sql_engine = os.getenv("SPICE_DUNE_RAW_SQL_ENGINE", "execution_sql")
            try:
                if q_type == "query_id":
                    q_id_value = int(q_use)
                elif q_type == "url":
                    q_id_value = dune_urls.get_query_id(q_use)
                else:
                    # raw SQL: only use template id if using template engine
                    if raw_sql_engine == "template":
                        tmpl = os.getenv("SPICE_RAW_SQL_QUERY_ID", "4060379")
                        template_id_value = int(tmpl)
            except Exception:
                pass

            extra_fields: dict[str, Any] = {}
            if q_id_value is not None:
                extra_fields["query_id"] = q_id_value
            if template_id_value is not None:
                extra_fields["template_query_id"] = template_id_value

            # Compute query SHA256 for better debugging
            q_sha = None
            try:
                q_sha = self._persist_query_sql(q_use, q_type)
                if q_sha:
                    extra_fields["query_sha256"] = q_sha
            except Exception:
                pass

            self.query_history.record(
                execution_id="unknown",
                query_type=_categorize_query(query),
                query_preview=query,
                status="error",
                duration_ms=duration_ms,
                error=str(exc),
                **extra_fields,
            )

            enriched = self._enrich_error(exc)
            context = {"tool": "dune_query", "query": q_use, "query_type": _categorize_query(q_use)}
            if enriched:
                context.update(enriched)
            
            # Add debugging information for raw SQL failures
            if q_type == "raw_sql" and "could not determine execution" in str(exc):
                context.update({
                    "debug_info": "Raw SQL execution failed - check template query configuration and API key",
                    "template_query_id": template_id_value,
                    "environment_vars": {
                        "SPICE_RAW_SQL_QUERY_ID": os.getenv("SPICE_RAW_SQL_QUERY_ID"),
                        "DUNE_API_KEY_present": bool(os.getenv("DUNE_API_KEY"))
                    },
                    "suggested_action": "Retry or check if the template query (4060379) is accessible"
                })
            
            return error_response(exc, context=context)

    def _persist_query_sql(self, query: str, q_type: str) -> str | None:
        compute_fn = getattr(self.query_history, "compute_query_sha256", None)
        write_fn = getattr(self.query_history, "write_sql_artifact", None)
        if compute_fn is None or write_fn is None:
            return None

        if q_type == "raw_sql":
            sha = compute_fn(query)
            write_fn(query, sha)
            return sha

        try:
            query_id = dune_urls.get_query_id(query)
            headers = {
                "X-Dune-API-Key": dune_urls.get_api_key(),
                "User-Agent": get_dune_user_agent(),
            }
            resp = self._http.request(
                "GET",
                f"https://api.dune.com/api/v1/query/{query_id}",
                headers=headers,
                timeout=10.0,
            )
            data = resp.json()
            sql = data.get("query_sql")
            if isinstance(sql, str) and sql:
                sha = compute_fn(sql)
                write_fn(sql, sha)
                return sha
        except Exception:
            return None
        return None

    def _enrich_error(self, error: Exception) -> dict[str, Any]:
        enriched: dict[str, Any] = {}
        try:
            import re

            match = re.search(r"execution_id=([A-Za-z0-9]+)", str(error))
            if match:
                execution_id = match.group(1)
                url = dune_urls.get_execution_status_url(execution_id)
                headers = {
                    "X-Dune-API-Key": dune_urls.get_api_key(),
                    "User-Agent": get_dune_user_agent(),
                }
                resp = self._http.request("GET", url, headers=headers, timeout=10.0)
                data = resp.json()
                if isinstance(data, dict):
                    enriched.update(
                        {
                            "dune_state": data.get("state"),
                            "dune_error": data.get("error"),
                            "execution_started_at": data.get("execution_started_at"),
                            "execution_ended_at": data.get("execution_ended_at"),
                        }
                    )
        except Exception:
            pass
        return enriched


def _categorize_query(q: str) -> str:
    if q.startswith("https://") or q.startswith("dune.com/queries") or q.startswith(
        "https://api.dune.com/api/v1/query/"
    ):
        return "url"
    try:
        int(q)
        return "query_id"
    except ValueError:
        return "raw_sql"


def _maybe_rewrite_show_sql(sql: str) -> str | None:
    """DEPRECATED: This function is no longer used.
    
    Native SHOW statements are now used directly as they're faster than
    information_schema queries in Dune. See issue #10 for details.
    
    This function is kept for backward compatibility but is not called.
    """
    # Function body kept for reference but not executed
    return None
