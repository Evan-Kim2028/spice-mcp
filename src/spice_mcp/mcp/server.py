from __future__ import annotations

import logging
import os
from typing import Any, Literal

os.environ.setdefault("FASTMCP_NO_BANNER", "1")
os.environ.setdefault("FASTMCP_LOG_LEVEL", "ERROR")
import sys as _sys

# Redirect potential import-time output to stderr (defensive)
_orig_stdout = _sys.stdout
_sys.stdout = _sys.stderr
from fastmcp import FastMCP
from fastmcp import settings as fastmcp_settings

_sys.stdout = _orig_stdout

# Ensure CLI banner is disabled to keep MCP stdout clean
try:
    fastmcp_settings.show_cli_banner = False  # type: ignore[attr-defined]
except Exception:
    pass

from ..adapters.dune import extract as dune_extract
from ..adapters.dune import urls as dune_urls
from ..adapters.dune.admin import DuneAdminAdapter
from ..adapters.dune.client import DuneAdapter
from ..adapters.http_client import HttpClient
from ..config import Config
from ..core.errors import error_response
from ..logging.query_history import QueryHistory
from ..service_layer.discovery_service import DiscoveryService
from ..service_layer.query_admin_service import QueryAdminService
from ..service_layer.query_service import QueryService
from ..service_layer.sui_service import SuiService
from .tools.execute_query import ExecuteQueryTool
from .tools.sui_package_overview import SuiPackageOverviewTool

logger = logging.getLogger(__name__)


# Global handles initialized on demand
CONFIG: Config | None = None
QUERY_HISTORY: QueryHistory | None = None
DUNE_ADAPTER: DuneAdapter | None = None
QUERY_SERVICE: QueryService | None = None
QUERY_ADMIN_SERVICE: QueryAdminService | None = None
SEMAPHORE = None
DISCOVERY_SERVICE: DiscoveryService | None = None
SUI_SERVICE: SuiService | None = None
HTTP_CLIENT: HttpClient | None = None

EXECUTE_QUERY_TOOL: ExecuteQueryTool | None = None
SUI_OVERVIEW_TOOL: SuiPackageOverviewTool | None = None


app = FastMCP("spice-mcp")


def _ensure_initialized() -> None:
    """Initialize configuration and tool instances if not already initialized."""
    global CONFIG, QUERY_HISTORY, DUNE_ADAPTER, QUERY_SERVICE, DISCOVERY_SERVICE, SUI_SERVICE, QUERY_ADMIN_SERVICE
    global EXECUTE_QUERY_TOOL, SUI_OVERVIEW_TOOL, HTTP_CLIENT

    if CONFIG is not None and EXECUTE_QUERY_TOOL is not None:
        return

    logger.info("Initializing spice-mcp (fastmcp) server...")
    # Best-effort: load .env if DUNE_API_KEY missing
    if not os.environ.get("DUNE_API_KEY") and not os.environ.get("SPICE_MCP_SKIP_DOTENV"):
        for candidate in (os.path.join(os.getcwd(), ".env"), os.path.expanduser("~/.env")):
            try:
                if os.path.exists(candidate):
                    with open(candidate, encoding="utf-8") as f:
                        for line in f:
                            line=line.strip()
                            if not line or line.startswith('#') or '=' not in line:
                                continue
                            k,v = line.split('=',1)
                            k=k.strip(); v=v.strip()
                            if k and v and k not in os.environ:
                                os.environ[k]=v
            except Exception:
                pass
    CONFIG = Config.from_env()
    QUERY_HISTORY = QueryHistory.from_env()
    HTTP_CLIENT = HttpClient(CONFIG.http)
    DUNE_ADAPTER = DuneAdapter(CONFIG, http_client=HTTP_CLIENT)
    QUERY_SERVICE = QueryService(DUNE_ADAPTER)
    DISCOVERY_SERVICE = DiscoveryService(DUNE_ADAPTER)
    QUERY_ADMIN_SERVICE = QueryAdminService(
        DuneAdminAdapter(
            CONFIG.dune.api_key,
            http_client=HTTP_CLIENT,
            http_config=CONFIG.http,
        )
    )
    SUI_SERVICE = SuiService(QUERY_SERVICE)

    EXECUTE_QUERY_TOOL = ExecuteQueryTool(CONFIG, QUERY_SERVICE, QUERY_HISTORY)
    SUI_OVERVIEW_TOOL = SuiPackageOverviewTool(SUI_SERVICE)
    # Concurrency gate for heavy query executions
    try:
        import asyncio
        global SEMAPHORE
        SEMAPHORE = asyncio.Semaphore(CONFIG.max_concurrent_queries)
    except Exception:
        pass

    logger.info("spice-mcp server ready (fastmcp)!")


def _best_effort_load_dotenv() -> None:
    """Load a local .env (repo or home) if present and not explicitly disabled."""
    if os.environ.get("SPICE_MCP_SKIP_DOTENV"):
        return
    if os.environ.get("DUNE_API_KEY"):
        return
    for candidate in (os.path.join(os.getcwd(), ".env"), os.path.expanduser("~/.env")):
        try:
            if os.path.exists(candidate):
                with open(candidate, encoding="utf-8") as f:
                    for line in f:
                        line=line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        k,v = line.split('=',1)
                        k=k.strip(); v=v.strip()
                        if k and v and k not in os.environ:
                            os.environ[k]=v
        except Exception:
            pass


def compute_health_status() -> dict[str, Any]:
    """Compute a lightweight health status without requiring full init."""
    if not os.getenv("DUNE_API_KEY"):
        _best_effort_load_dotenv()
    has_api_key = bool(os.getenv("DUNE_API_KEY") or (CONFIG and CONFIG.dune.api_key))
    qh = QUERY_HISTORY if QUERY_HISTORY is not None else QueryHistory.from_env()
    history_path = getattr(qh, "history_path", None)
    status: dict[str, Any] = {
        "api_key_present": has_api_key,
        "query_history_path": str(history_path) if history_path else None,
        "logging_enabled": qh is not None,
        "status": "ok" if has_api_key else "degraded",
    }

    # Optional: check raw SQL template query health if configured
    try:
        tmpl = os.getenv("SPICE_RAW_SQL_QUERY_ID")
        if tmpl:
            tid = dune_urls.get_query_id(tmpl)
            url = dune_urls.url_templates["query"].format(query_id=tid)
            headers = {
                "X-Dune-API-Key": os.getenv("DUNE_API_KEY", ""),
                "User-Agent": dune_extract.get_user_agent(),
            }
            client = HTTP_CLIENT or HttpClient(Config.from_env().http)
            resp = client.request("GET", url, headers=headers, timeout=5.0)
            status["template_query_id"] = tid
            status["template_query_ok"] = resp.status_code == 200
    except Exception:
        pass

    return status


@app.tool(
    name="dune_query_info",
    title="Query Info",
    description="Fetch Dune query metadata (name, parameters, tags, SQL).",
    tags={"dune", "query"},
)
async def dune_query_info(query: str) -> dict[str, Any]:
    _ensure_initialized()
    try:
        qid = dune_urls.get_query_id(query)
        url = dune_urls.url_templates["query"].format(query_id=qid)
        headers = {
            "X-Dune-API-Key": dune_urls.get_api_key(),
            "User-Agent": dune_extract.get_user_agent(),
        }
        client = HTTP_CLIENT or HttpClient(Config.from_env().http)
        resp = client.request("GET", url, headers=headers, timeout=10.0)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        # Select useful fields; fall back gracefully if missing
        payload = {
            "ok": resp.ok,
            "status": resp.status_code,
            "query_id": qid,
            "name": data.get("name"),
            "description": data.get("description"),
            "tags": data.get("tags"),
            "parameters": data.get("parameters"),
            "version": data.get("version"),
            "query_sql": data.get("query_sql"),
            "query_url": f"https://dune.com/queries/{qid}",
        }
        return payload
    except Exception as e:
        return error_response(e, context={
            "tool": "dune_query_info",
            "query": query,
        })


@app.tool(
    name="dune_query",
    title="Run Dune Query",
    description="Execute Dune queries and return agent-optimized preview.",
    tags={"dune", "query"},
)
async def dune_query(
    query: str,
    parameters: dict[str, Any] | None = None,
    refresh: bool = False,
    max_age: float | None = None,
    limit: int | None = None,
    offset: int | None = None,
    sample_count: int | None = None,
    sort_by: str | None = None,
    columns: list[str] | None = None,
    format: Literal["preview", "raw", "metadata", "poll"] = "preview",
    extras: dict[str, Any] | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    _ensure_initialized()
    assert EXECUTE_QUERY_TOOL is not None
    try:
        # Execute query directly without semaphore concurrency control
        return await EXECUTE_QUERY_TOOL.execute(
            query=query,
            parameters=parameters,
            refresh=refresh,
            max_age=max_age,
            limit=limit,
            offset=offset,
            sample_count=sample_count,
            sort_by=sort_by,
            columns=columns,
            format=format,
            extras=extras,
            timeout_seconds=timeout_seconds,
        )
    except Exception as e:
        return error_response(e, context={
            "tool": "dune_query",
            "query": query,
            "limit": limit,
            "offset": offset,
        })


@app.tool(
    name="dune_health_check",
    title="Health Check",
    description="Validate Dune API key presence and logging setup.",
    tags={"health"},
)
async def dune_health_check() -> dict[str, Any]:
    return compute_health_status()


async def _dune_find_tables_impl(
    keyword: str | None = None,
    schema: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    _ensure_initialized()
    assert DISCOVERY_SERVICE is not None
    out: dict[str, Any] = {}
    if keyword:
        out["schemas"] = DISCOVERY_SERVICE.find_schemas(keyword)
    if schema:
        tables = DISCOVERY_SERVICE.list_tables(schema, limit=limit)
        out["tables"] = [summary.table for summary in tables]
    return out


@app.tool(
    name="dune_find_tables",
    title="Find Tables",
    description="Search schemas and optionally list tables.",
    tags={"dune", "schema"},
)
async def dune_find_tables(keyword: str | None = None, schema: str | None = None, limit: int = 50) -> dict[str, Any]:
    try:
        return await _dune_find_tables_impl(keyword=keyword, schema=schema, limit=limit)
    except Exception as e:
        return error_response(e, context={
            "tool": "dune_find_tables",
            "keyword": keyword,
            "schema": schema,
        })


async def _dune_describe_table_impl(schema: str, table: str) -> dict[str, Any]:
    _ensure_initialized()
    assert DISCOVERY_SERVICE is not None
    desc = DISCOVERY_SERVICE.describe_table(schema, table)
    cols = []
    for col in desc.columns:
        cols.append(
            {
                "name": col.name,
                "dune_type": col.dune_type,
                "polars_dtype": col.polars_dtype,
                "extra": col.extra,
                "comment": col.comment,
            }
        )
    return {"columns": cols, "table": desc.fully_qualified_name}


@app.tool(
    name="dune_describe_table",
    title="Describe Table",
    description="Describe columns for a schema.table on Dune.",
    tags={"dune", "schema"},
)
async def dune_describe_table(schema: str, table: str) -> dict[str, Any]:
    try:
        return await _dune_describe_table_impl(schema=schema, table=table)
    except Exception as e:
        return error_response(e, context={
            "tool": "dune_describe_table",
            "schema": schema,
            "table": table,
        })


@app.tool(
    name="sui_package_overview",
    title="Sui Package Overview",
    description="Compact overview for Sui package activity.",
    tags={"sui"},
)
async def sui_package_overview(
    packages: list[str],
    hours: int = 72,
    timeout_seconds: float | None = 30,
) -> dict[str, Any]:
    _ensure_initialized()
    assert SUI_OVERVIEW_TOOL is not None
    try:
        return await SUI_OVERVIEW_TOOL.execute(
            packages=packages, hours=hours, timeout_seconds=timeout_seconds
        )
    except Exception as e:
        return error_response(e, context={
            "tool": "sui_package_overview",
            "packages": packages,
            "hours": hours,
        })


@app.resource(uri="spice:sui/events_preview/{hours}/{limit}/{packages}", name="Sui Events Preview", description="Preview Sui events (3-day default) for comma-separated packages; returns JSON.")
async def sui_events_preview_resource(hours: str, limit: str, packages: str) -> str:
    import json

    try:
        hh = int(hours)
    except Exception:
        hh = 72
    try:
        ll = int(limit)
    except Exception:
        ll = 50
    pkgs = []
    if packages and packages != "_":
        pkgs = [p.strip() for p in packages.split(",") if p.strip()]

    _ensure_initialized()
    assert SUI_SERVICE is not None
    try:
        result = SUI_SERVICE.events_preview(pkgs, hours=hh, limit=ll)
        payload = {"ok": True, **result}
    except Exception as exc:
        payload = error_response(
            exc,
            context={
                "resource": "sui_events_preview",
                "packages": pkgs,
                "hours": hh,
                "limit": ll,
            },
        )
    return json.dumps(payload)


# Resources
@app.resource(uri="spice:history/tail/{n}", name="Query History Tail", description="Tail last N lines from query history")
async def history_tail(n: str) -> str:
    from collections import deque
    try:
        nn = int(n)
    except Exception:
        nn = 50
    # Clamp to a reasonable bound to avoid excessive memory use
    if nn < 1:
        nn = 1
    if nn > 1000:
        nn = 1000
    qh = QUERY_HISTORY if QUERY_HISTORY is not None else QueryHistory.from_env()
    path = getattr(qh, "history_path", None)
    if path is None or not os.path.exists(path):
        return ""
    try:
        buf = deque(maxlen=nn)
        with open(path, encoding="utf-8") as f:
            for line in f:
                buf.append(line)
        return "".join(buf)
    except Exception:
        return ""


@app.resource(uri="spice:artifact/{sha}", name="SQL Artifact", description="SQL artifact by SHA-256")
async def sql_artifact(sha: str) -> str:
    import os
    import re

    if not re.fullmatch(r"[a-f0-9]{64}", sha):
        return ""

    qh = QUERY_HISTORY if QUERY_HISTORY is not None else QueryHistory.from_env()
    base = getattr(qh, "artifact_root", None)
    if base is None:
        return ""
    path = os.path.join(str(base), "queries", "by_sha", f"{sha}.sql")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


@app.resource(
    uri="spice:sui/package_overview/{hours}/{timeout_seconds}/{packages}",
    name="Sui Package Overview (cmd)",
    description="Compact overview for Sui package activity as a command-style resource."
)
async def sui_package_overview_cmd(hours: str, timeout_seconds: str, packages: str) -> str:
    import json

    try:
        hh = int(hours)
    except Exception:
        hh = 72
    try:
        tt = float(timeout_seconds)
    except Exception:
        tt = 30.0
    pkgs = []
    if packages and packages != "_":
        pkgs = [p.strip() for p in packages.split(",") if p.strip()]

    _ensure_initialized()
    assert SUI_SERVICE is not None
    try:
        result = SUI_SERVICE.package_overview(pkgs, hours=hh, timeout_seconds=tt)
    except Exception as exc:
        result = error_response(
            exc,
            context={
                "resource": "sui_package_overview",
                "packages": pkgs,
                "hours": hh,
                "timeout_seconds": tt,
            },
        )
    return json.dumps(result)


def main() -> None:
    # Do not initialize at startup; defer until first tool call so env issues
    # don't break MCP handshake. Disable banner to keep stdio clean.
    app.run(show_banner=False)


if __name__ == "__main__":
    main()
@app.tool(
    name="dune_query_create",
    title="Create Saved Query",
    description="Create a new saved Dune query (name + SQL).",
    tags={"dune", "admin"},
)
async def dune_query_create(name: str, query_sql: str, description: str | None = None, tags: list[str] | None = None, parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    _ensure_initialized()
    assert QUERY_ADMIN_SERVICE is not None
    try:
        return dict(QUERY_ADMIN_SERVICE.create(name=name, query_sql=query_sql, description=description, tags=tags, parameters=parameters))
    except Exception as e:
        return error_response(e, context={"tool": "dune_query_create", "name": name})


@app.tool(
    name="dune_query_update",
    title="Update Saved Query",
    description="Update fields of a saved Dune query (name/SQL/description/tags/parameters).",
    tags={"dune", "admin"},
)
async def dune_query_update(query_id: int, name: str | None = None, query_sql: str | None = None, description: str | None = None, tags: list[str] | None = None, parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    _ensure_initialized()
    assert QUERY_ADMIN_SERVICE is not None
    try:
        return dict(QUERY_ADMIN_SERVICE.update(query_id, name=name, query_sql=query_sql, description=description, tags=tags, parameters=parameters))
    except Exception as e:
        return error_response(e, context={"tool": "dune_query_update", "query_id": query_id})


@app.tool(
    name="dune_query_fork",
    title="Fork Saved Query",
    description="Fork an existing saved Dune query.",
    tags={"dune", "admin"},
)
async def dune_query_fork(source_query_id: int, name: str | None = None) -> dict[str, Any]:
    _ensure_initialized()
    assert QUERY_ADMIN_SERVICE is not None
    try:
        return dict(QUERY_ADMIN_SERVICE.fork(source_query_id, name=name))
    except Exception as e:
        return error_response(e, context={"tool": "dune_query_fork", "source_query_id": source_query_id})
