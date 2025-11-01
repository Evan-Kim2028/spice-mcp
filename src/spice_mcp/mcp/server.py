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

from ..adapters.dune import urls as dune_urls
from ..adapters.dune.admin import DuneAdminAdapter
from ..adapters.dune.client import DuneAdapter
from ..adapters.http_client import HttpClient
from ..adapters.spellbook.explorer import SpellbookExplorer
from ..config import Config
from ..core.errors import error_response
from ..logging.query_history import QueryHistory
from ..service_layer.discovery_service import DiscoveryService
from ..service_layer.query_admin_service import QueryAdminService
from ..service_layer.query_service import QueryService
from ..service_layer.verification_service import VerificationService
from .tools.execute_query import ExecuteQueryTool

logger = logging.getLogger(__name__)


# Global handles initialized on demand
CONFIG: Config | None = None
QUERY_HISTORY: QueryHistory | None = None
DUNE_ADAPTER: DuneAdapter | None = None
QUERY_SERVICE: QueryService | None = None
QUERY_ADMIN_SERVICE: QueryAdminService | None = None
DISCOVERY_SERVICE: DiscoveryService | None = None
SPELLBOOK_EXPLORER: SpellbookExplorer | None = None
HTTP_CLIENT: HttpClient | None = None
VERIFICATION_SERVICE: VerificationService | None = None

EXECUTE_QUERY_TOOL: ExecuteQueryTool | None = None


app = FastMCP("spice-mcp")


def _ensure_initialized() -> None:
    """Initialize configuration and tool instances if not already initialized."""
    global CONFIG, QUERY_HISTORY, DUNE_ADAPTER, QUERY_SERVICE, DISCOVERY_SERVICE, QUERY_ADMIN_SERVICE
    global EXECUTE_QUERY_TOOL, HTTP_CLIENT, SPELLBOOK_EXPLORER, VERIFICATION_SERVICE

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
    
    # Initialize Spellbook explorer (lazy, clones repo on first use)
    SPELLBOOK_EXPLORER = SpellbookExplorer()
    
    # Initialize verification service with persistent cache
    from pathlib import Path
    cache_dir = Path.home() / ".spice_mcp"
    cache_dir.mkdir(exist_ok=True)
    VERIFICATION_SERVICE = VerificationService(
        cache_path=cache_dir / "table_verification_cache.json",
        dune_adapter=DUNE_ADAPTER,
    )

    EXECUTE_QUERY_TOOL = ExecuteQueryTool(CONFIG, QUERY_SERVICE, QUERY_HISTORY)

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
            from ..adapters.dune.user_agent import get_user_agent as get_dune_user_agent
            headers = {
                "X-Dune-API-Key": os.getenv("DUNE_API_KEY", ""),
                "User-Agent": get_dune_user_agent(),
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
def dune_query_info(query: str) -> dict[str, Any]:
    _ensure_initialized()
    try:
        qid = dune_urls.get_query_id(query)
        url = dune_urls.url_templates["query"].format(query_id=qid)
        from ..adapters.dune.user_agent import get_user_agent as get_dune_user_agent
        headers = {
            "X-Dune-API-Key": dune_urls.get_api_key(),
            "User-Agent": get_dune_user_agent(),
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


def _dune_query_impl(
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
    """Internal implementation of dune_query to avoid FastMCP overload detection."""
    _ensure_initialized()
    assert EXECUTE_QUERY_TOOL is not None
    
    # Normalize parameters: handle case where MCP client passes JSON string
    # This can happen if FastMCP's schema generation doesn't match client expectations
    normalized_parameters = parameters
    if isinstance(parameters, str):
        try:
            import json
            normalized_parameters = json.loads(parameters)
        except (json.JSONDecodeError, TypeError):
            return error_response(
                ValueError(f"parameters must be a dict or JSON string, got {type(parameters).__name__}"),
                context={
                    "tool": "dune_query",
                    "query": query,
                    "parameters_type": type(parameters).__name__,
                }
            )
    
    # Normalize extras similarly
    normalized_extras = extras
    if isinstance(extras, str):
        try:
            import json
            normalized_extras = json.loads(extras)
        except (json.JSONDecodeError, TypeError):
            normalized_extras = None
    
    try:
        # Execute query synchronously
        return EXECUTE_QUERY_TOOL.execute(
            query=query,
            parameters=normalized_parameters,
            refresh=refresh,
            max_age=max_age,
            limit=limit,
            offset=offset,
            sample_count=sample_count,
            sort_by=sort_by,
            columns=columns,
            format=format,
            extras=normalized_extras,
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
    name="dune_query",
    title="Run Dune Query",
    description="Execute Dune queries and return agent-optimized preview.",
    tags={"dune", "query"},
)
def dune_query(
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
    """Execute Dune queries (by ID, URL, or raw SQL) and return agent-optimized preview.
    
    ⚠️ IMPORTANT: ALWAYS use dune_discover FIRST to find verified table names.
    Do not guess table names or query information_schema directly.
    
    The query parameter accepts:
    - Query IDs (e.g., "123456")
    - Query URLs (e.g., "https://dune.com/queries/123456")
    - Raw SQL using tables discovered via dune_discover
    
    For Spellbook models, use the 'dune_table' field returned by dune_discover.
    Example: dune_discover(keyword="walrus") → returns dune_table="sui_walrus.base_table"
             Then use: dune_query(query="SELECT * FROM sui_walrus.base_table LIMIT 10")
    
    This wrapper ensures FastMCP doesn't detect overloads in imported functions.
    """
    # Always ensure parameters is explicitly passed (even if None) to avoid FastMCP
    # overload detection when the keyword is omitted
    return _dune_query_impl(
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


@app.tool(
    name="dune_health_check",
    title="Health Check",
    description="Validate Dune API key presence and logging setup.",
    tags={"health"},
)
def dune_health_check() -> dict[str, Any]:
    return compute_health_status()


def _unified_discover_impl(
    keyword: str | list[str] | None = None,
    schema: str | None = None,
    limit: int = 50,
    source: Literal["dune", "spellbook", "both"] = "both",
    include_columns: bool = True,
) -> dict[str, Any]:
    """
    Unified discovery implementation that can search Dune API, Spellbook repo, or both.
    
    Returns a consistent format with 'schemas' and 'tables' keys.
    """
    _ensure_initialized()
    out: dict[str, Any] = {
        "schemas": [],
        "tables": [],
        "source": source,
    }
    
    # Normalize keyword to list
    keywords = keyword if isinstance(keyword, list) else ([keyword] if keyword else [])
    
    # Search Dune API if requested
    if source in ("dune", "both"):
        dune_result: dict[str, Any] = {}
        if keyword:
            assert DISCOVERY_SERVICE is not None
            # Search each keyword and combine results
            # DISCOVERY_SERVICE.find_schemas returns list[str], not SchemaMatch objects
            all_schemas: set[str] = set()
            for kw in keywords:
                schemas = DISCOVERY_SERVICE.find_schemas(kw)
                # schemas is already a list of strings from DiscoveryService
                all_schemas.update(schemas)
            dune_result["schemas"] = sorted(list(all_schemas))
        
        if schema:
            assert DISCOVERY_SERVICE is not None
            tables = DISCOVERY_SERVICE.list_tables(schema, limit=limit)
            dune_result["tables"] = [
                {
                    "schema": schema,
                    "table": summary.table,
                    "fully_qualified_name": f"{schema}.{summary.table}",
                    "source": "dune",
                    "dune_table": f"{schema}.{summary.table}",
                    "verified": True,
                }
                for summary in tables
            ]
        
        # Merge Dune results
        if "schemas" in dune_result:
            out["schemas"].extend(dune_result["schemas"])
        if "tables" in dune_result:
            out["tables"].extend(dune_result["tables"])
    
    # Search Spellbook if requested
    if source in ("spellbook", "both"):
        spellbook_result = _spellbook_find_models_impl(
            keyword=keyword,
            schema=schema,
            limit=limit,
            include_columns=include_columns,
        )
        
        # Convert spellbook models to unified format
        if "schemas" in spellbook_result:
            spellbook_schemas = spellbook_result["schemas"]
            # Merge schemas (avoid duplicates)
            existing_schemas = set(out["schemas"])
            for s in spellbook_schemas:
                if s not in existing_schemas:
                    out["schemas"].append(s)
        
        if "models" in spellbook_result:
            for model in spellbook_result["models"]:
                table_info = {
                    "schema": model["schema"],
                    "table": model["table"],
                    "fully_qualified_name": model["fully_qualified_name"],
                    "source": "spellbook",
                    # Include resolved Dune table names
                    "dune_schema": model.get("dune_schema"),
                    "dune_alias": model.get("dune_alias"),
                    "dune_table": model.get("dune_table"),
                }
                if "columns" in model:
                    table_info["columns"] = model["columns"]
                out["tables"].append(table_info)
    
    # Verify Spellbook tables exist in Dune before returning
    if source in ("spellbook", "both") and out["tables"]:
        assert VERIFICATION_SERVICE is not None
        # Extract Spellbook tables that need verification
        spellbook_tables = [
            (t["dune_schema"], t["dune_alias"])
            for t in out["tables"]
            if t.get("source") == "spellbook" and t.get("dune_schema") and t.get("dune_alias")
        ]
        
        if spellbook_tables:
            # Verify tables exist (uses cache, queries Dune only if needed)
            verification_results = VERIFICATION_SERVICE.verify_tables_batch(spellbook_tables)

            # Filter: drop only tables explicitly verified as False.
            # Keep tables when verification is True or inconclusive (missing).
            verified_tables = []
            for t in out["tables"]:
                if t.get("source") != "spellbook":
                    # Keep Dune tables as-is
                    verified_tables.append(t)
                    continue
                dune_fqn = t.get("dune_table")
                if not dune_fqn:
                    # If we couldn't resolve dune_table, keep it (conservative)
                    verified_tables.append(t)
                    continue
                vr = verification_results.get(dune_fqn)
                if vr is False:
                    # Explicitly known to be non-existent -> drop
                    continue
                if vr is True:
                    t["verified"] = True
                # If vr is None/missing (inconclusive), keep without setting verified
                verified_tables.append(t)
            
            out["tables"] = verified_tables
            
            # Add helpful message if no tables found
            if not out["tables"] and len(spellbook_tables) > 0:
                out["message"] = "No verified tables found. Try different keywords or check schema names."
    
    # Deduplicate and sort schemas
    out["schemas"] = sorted(list(set(out["schemas"])))
    
    # Limit total tables
    if limit and len(out["tables"]) > limit:
        out["tables"] = out["tables"][:limit]
    
    return out


@app.tool(
    name="dune_discover",
    title="Discover Tables",
    description="Unified tool to discover tables/models from Dune API and/or Spellbook repository. Search by keyword(s) or list tables in a schema.",
    tags={"dune", "spellbook", "schema", "discovery"},
)
def dune_discover(
    keyword: str | list[str] | None = None,
    schema: str | None = None,
    limit: int = 50,
    source: Literal["dune", "spellbook", "both"] = "both",
    include_columns: bool = True,
) -> dict[str, Any]:
    """
    PRIMARY discovery tool for finding tables in Dune.
    
    ⚠️ IMPORTANT: ALWAYS use this tool instead of querying information_schema directly.
    Querying information_schema is slow and causes lag. This tool uses optimized
    native SHOW statements for fast discovery.
    
    This tool automatically:
    - Parses dbt configs from Spellbook models to resolve actual Dune table names
    - Verifies tables exist in Dune before returning them
    - Returns ONLY verified, queryable tables
    
    All returned tables are VERIFIED to exist - you can query them immediately using
    the 'dune_table' field.
    
    Args:
        keyword: Search term(s) - can be a string or list of strings
                 (e.g., "layerzero", ["layerzero", "dex"], "nft")
        schema: Schema name to list tables from (e.g., "dex", "spellbook", "layerzero")
        limit: Maximum number of tables to return
        source: Where to search - "dune" (Dune API only), "spellbook" (GitHub repo only),
                or "both" (default: searches both and merges results)
        include_columns: Whether to include column details for Spellbook models (default: True)
    
    Returns:
        Dictionary with:
        - 'schemas': List of matching schema names
        - 'tables': List of table/model objects, each with:
          - schema: Schema name (Spellbook subproject name)
          - table: Table/model name (Spellbook model name)
          - fully_qualified_name: schema.table (Spellbook format)
          - source: "dune" or "spellbook"
          - dune_schema: Actual Dune schema name (for Spellbook models)
          - dune_alias: Actual Dune table alias (for Spellbook models)
          - dune_table: Verified, queryable Dune table name (e.g., "sui_walrus.base_table")
          - verified: True (all returned tables are verified to exist)
          - columns: Column details (for Spellbook models, if include_columns=True)
        - 'source': The source parameter used
        - 'message': Helpful message if no tables found
    
    Examples:
        # Search both sources for walrus - returns verified tables only
        dune_discover(keyword="walrus")
        # → Returns tables with dune_table field like "sui_walrus.base_table"
        
        # Use the dune_table field to query immediately
        dune_query(query="SELECT * FROM sui_walrus.base_table LIMIT 10")
        
        # Search only Spellbook
        dune_discover(keyword=["layerzero", "bridge"], source="spellbook")
        
        # Search only Dune API
        dune_discover(keyword="sui", source="dune")
        
        # List all tables in a schema (searches both sources)
        dune_discover(schema="dex")
    """
    try:
        return _unified_discover_impl(
            keyword=keyword,
            schema=schema,
            limit=limit,
            source=source,
            include_columns=include_columns,
        )
    except Exception as e:
        return error_response(e, context={
            "tool": "dune_discover",
            "keyword": keyword,
            "schema": schema,
            "source": source,
        })


def _dune_describe_table_impl(schema: str, table: str) -> dict[str, Any]:
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
def dune_describe_table(schema: str, table: str) -> dict[str, Any]:
    try:
        return _dune_describe_table_impl(schema=schema, table=table)
    except Exception as e:
        return error_response(e, context={
            "tool": "dune_describe_table",
            "schema": schema,
            "table": table,
        })


def _spellbook_find_models_impl(
    keyword: str | list[str] | None = None,
    schema: str | None = None,
    limit: int = 50,
    include_columns: bool = True,
) -> dict[str, Any]:
    """
    Implementation for spellbook model discovery.
    
    Supports searching by keyword(s) and optionally includes column details.
    """
    _ensure_initialized()
    assert SPELLBOOK_EXPLORER is not None
    out: dict[str, Any] = {}
    
    # Handle keyword search (string or list)
    if keyword:
        # Normalize to list
        keywords = keyword if isinstance(keyword, list) else [keyword]
        
        # Find schemas matching any keyword
        all_schemas: set[str] = set()
        for kw in keywords:
            schemas = SPELLBOOK_EXPLORER.find_schemas(kw)
            all_schemas.update(match.schema for match in schemas)
        
        out["schemas"] = sorted(list(all_schemas))
        
        # If schema not specified but we found schemas, search models in those schemas
        if not schema and all_schemas:
            out["models"] = []
            for schema_name in sorted(all_schemas):
                tables = SPELLBOOK_EXPLORER.list_tables(schema_name, limit=limit)
                for table_summary in tables:
                    # Check if table name matches any keyword
                    table_name = table_summary.table.lower()
                    matches_keyword = any(kw.lower() in table_name for kw in keywords)
                    
                    if matches_keyword:
                        # Get model details including resolved Dune table names
                        models_dict = SPELLBOOK_EXPLORER._load_models()
                        model_details = None
                        for m in models_dict.get(schema_name, []):
                            if m["name"] == table_summary.table:
                                model_details = m
                                break
                        
                        model_info: dict[str, Any] = {
                            "schema": schema_name,
                            "table": table_summary.table,
                            "fully_qualified_name": f"{schema_name}.{table_summary.table}",
                            # Include resolved Dune table names if available
                            "dune_schema": model_details.get("dune_schema") if model_details else None,
                            "dune_alias": model_details.get("dune_alias") if model_details else None,
                            "dune_table": model_details.get("dune_table") if model_details else None,
                        }
                        
                        # Include column details if requested
                        if include_columns:
                            try:
                                desc = SPELLBOOK_EXPLORER.describe_table(schema_name, table_summary.table)
                                model_info["columns"] = [
                                    {
                                        "name": col.name,
                                        "dune_type": col.dune_type,
                                        "polars_dtype": col.polars_dtype,
                                        "comment": col.comment,
                                    }
                                    for col in desc.columns
                                ]
                            except Exception:
                                model_info["columns"] = []
                        
                        out["models"].append(model_info)
            
            # Limit total models returned
            if limit and len(out["models"]) > limit:
                out["models"] = out["models"][:limit]
    
    # If schema specified, list all tables in that schema
    if schema:
        tables = SPELLBOOK_EXPLORER.list_tables(schema, limit=limit)
        if "models" not in out:
            out["models"] = []
        
        for table_summary in tables:
            # Get model details including resolved Dune table names
            models_dict = SPELLBOOK_EXPLORER._load_models()
            model_details = None
            for m in models_dict.get(schema, []):
                if m["name"] == table_summary.table:
                    model_details = m
                    break
            
            model_info: dict[str, Any] = {
                "schema": schema,
                "table": table_summary.table,
                "fully_qualified_name": f"{schema}.{table_summary.table}",
                # Include resolved Dune table names if available
                "dune_schema": model_details.get("dune_schema") if model_details else None,
                "dune_alias": model_details.get("dune_alias") if model_details else None,
                "dune_table": model_details.get("dune_table") if model_details else None,
            }
            
            # Include column details if requested
            if include_columns:
                try:
                    desc = SPELLBOOK_EXPLORER.describe_table(schema, table_summary.table)
                    model_info["columns"] = [
                        {
                            "name": col.name,
                            "dune_type": col.dune_type,
                            "polars_dtype": col.polars_dtype,
                            "comment": col.comment,
                        }
                        for col in desc.columns
                    ]
                except Exception:
                    model_info["columns"] = []
            
            out["models"].append(model_info)
    
    return out


# Resources
@app.resource(uri="spice:history/tail/{n}", name="Query History Tail", description="Tail last N lines from query history")
def history_tail(n: str) -> str:
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
def sql_artifact(sha: str) -> str:
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
def dune_query_create(name: str, query_sql: str, description: str | None = None, tags: list[str] | None = None, parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
def dune_query_update(query_id: int, name: str | None = None, query_sql: str | None = None, description: str | None = None, tags: list[str] | None = None, parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
def dune_query_fork(source_query_id: int, name: str | None = None) -> dict[str, Any]:
    _ensure_initialized()
    assert QUERY_ADMIN_SERVICE is not None
    try:
        return dict(QUERY_ADMIN_SERVICE.fork(source_query_id, name=name))
    except Exception as e:
        return error_response(e, context={"tool": "dune_query_fork", "source_query_id": source_query_id})
