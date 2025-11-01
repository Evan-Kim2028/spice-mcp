# Architecture Overview

```
┌────────────┐    ┌────────────────────────┐    ┌─────────────────────────┐
│  MCP CLI   │ -> │ spice_mcp.mcp.server   │ -> │ Service Layer (Query,   │
│ (Codex UI) │    │  (FastMCP stdio)       │    │ Discovery, Sui)         │
└────────────┘    └────────────────────────┘    └────────────┬────────────┘
                                                             │
                                                             ▼
                                              ┌─────────────────────────┐
                                              │   Adapters (Dune)       │
                                              │ - adapters.dune.client  │
                                              │ - adapters.dune.extract │
                                              │ - adapters.dune.urls    │
                                              │ - adapters.dune.cache   │
                                              └────────────┬────────────┘
                                                             │
                                                             ▼
                                              ┌─────────────────────────┐
                                              │   Dune API / Storage    │
                                              └─────────────────────────┘
```

## Layers

### Core (`src/spice_mcp/core`)
- `models.py` – dataclass representations for query requests, previews, metadata, schema descriptions, and Sui artefacts.
- `ports.py` – protocols defining the boundaries (`QueryExecutor`, `CatalogExplorer`, `SuiInspector`).
- `errors.py` – MCP-oriented error categorisation and envelope helpers (`error_response`).

These modules contain zero infrastructure concerns; they define the shapes that higher layers orchestrate.

### Adapters (`src/spice_mcp/adapters`)
- `dune/client.py` – concrete implementation of the `QueryExecutor` and `CatalogExplorer` ports. It wraps the vendored Spice logic moved into `adapters.dune.extract`, `cache`, and `urls`.
- `dune/extract.py`, `dune/urls.py`, `dune/cache.py`, `dune/types.py` – battle-tested pieces from the original Spice client, namespaced under `adapters.dune`.
- Keeps Polars parsing, pagination, caching, and metadata enrichment close to the transport boundary.
- Responsible for ensuring the Dune API key is available (`DUNE_API_KEY`) and honouring `Config.cache.cache_dir`.

### Service Layer (`src/spice_mcp/service_layer`)
- `query_service.py` – orchestrates `QueryExecutor` calls and shapes the dictionaries returned to MCP tools. Handles `performance` passthrough, metadata merging, and preview formatting.
- `discovery_service.py` – thin façade around `CatalogExplorer`, returning friendlier lists for schema/table introspection.
- `sui_service.py` – composes `QueryService` to deliver Sui-specific behaviours (events preview, package overview defaults).

Services are pure Python and easily testable with stubbed ports (see `tests/tools/test_query_service.py`).

### MCP Integration (`src/spice_mcp/mcp`)
- `server.py` – FastMCP stdio bridge. Lazily initialises configuration, adapters, services, tools, and resources. Provides resource URIs and tools while keeping stdout clean.
- `tools/execute_query.py`, `tools/sui_package_overview.py` – thin glue calling into services, handling logging/audit trails, and shaping agent-friendly responses.
- Uses `QueryHistory` (`src/spice_mcp/logging/query_history.py`) for JSONL audit trails and SQL artefact storage.

### Observability (`src/spice_mcp/observability`)
- `logging.py` – centralised logging configuration (currently lightweight wrapper over `logging.basicConfig`).


## Configuration & Environment
- `Config` (`src/spice_mcp/config.py`) reads `DUNE_API_KEY`, cache settings, and timeouts.
- `_ensure_initialized` honours `SPICE_MCP_SKIP_DOTENV=1` to bypass automatic `.env` loading (useful for tests).
- Secrets: never store `DUNE_API_KEY` in Codex config; inherit from shell or CI secret management.

## Data Flow – `dune_query`
1. FastMCP receives the tool call, ensuring services are initialised.
2. `ExecuteQueryTool` builds request parameters (including `performance`).
3. `QueryService.execute` converts the call to a `QueryRequest` and delegates to `DuneAdapter.execute`.
4. `DuneAdapter.execute` invokes `extract.query`, handles caching, and builds a `QueryResult`.
5. Metadata (JSON result headers, pagination hints) is fetched via `fetch_metadata`.
6. Tool logs to `QueryHistory`, persists SQL artefacts, and returns a preview payload.

## Testing Strategy
- Unit tests target each layer:
  - `tests/offline/test_parsing.py`, `test_urls.py`, `test_cache.py` cover adapter helpers.
  - `tests/tools/test_query_service.py`, `test_execute_query_tool.py` validate service/tool orchestration using stubs.
  - `tests/fastmcp/` ensure FastMCP wiring works with monkeypatched adapters.
- HTTP boundary testing via `responses` in `tests/http_stubbed/`.
- Live tests are opt-in (`SPICE_TEST_LIVE=1`) and hit the real Dune API.

Adding new functionality? Start by defining a port or extending existing models, implement concrete behaviour in an adapter, compose it in the service layer, then surface it through the MCP tooling. Update or add tests at the appropriate layers to cover the new flow.
