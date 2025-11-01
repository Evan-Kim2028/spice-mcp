# spice-mcp

spice-mcp is an MCP server for [Dune](https://dune.com/) Analytics. It wraps a curated subset of the original Spice client inside a clean architecture (`core` models/ports → `adapters.dune` → service layer → FastMCP tools) and adds agent-friendly workflows for discovery and Sui package exploration. Results are Polars-first in Python and compact, token-efficient in MCP responses.

Requirements: Python 3.13+

This project uses FastMCP for typed, decorator-registered tools and resources.

## Highlights
- Polars LazyFrame-first pipeline: results stay lazy until explicitly materialized
- Ports/adapters layering for maintainable integrations ([docs/architecture.md](docs/architecture.md))
- Discovery utilities (find schemas/tables, describe columns)
- Sui package workflows (events/transactions/objects) with safe defaults
- JSONL query history + SQL artifacts (SHA-256) for reproducibility
- Rich MCP surface: query info/run, discovery, health, Sui, and Dune admin (create/update/fork)

## What is Dune?
[Dune](https://dune.com/) is a crypto data platform providing curated blockchain datasets and a public API to run and fetch query results. See the [Dune Docs](https://dune.com/docs) and [Dune API](https://dune.com/docs/api/) for full details.

## Quick Start
- Export `DUNE_API_KEY` in your shell (the server can also load a local `.env`; set `SPICE_MCP_SKIP_DOTENV=1` to skip during tests).
- Install dependencies (`uv sync` or `pip install -e .`).
- Start the FastMCP stdio server:
  - `python -m spice_mcp.mcp.server --env PYTHONPATH=$(pwd)/src`
  - or install the console script via `uv tool install .` and run `spice-mcp`.

## Cursor IDE Setup

To use spice-mcp with Cursor IDE:

1. **Install the MCP Server**:
   ```bash
   # Install dependencies and package
   uv sync
   pip install -e .
   
   # Or install via uv tool (creates console script)
   uv tool install .
   ```

2. **Configure Cursor**:
   - Open Cursor Settings → MCP Servers
   - Add new MCP server configuration:
   ```json
   {
     "name": "spice-mcp",
     "command": "spice-mcp",
     "env": {
       "DUNE_API_KEY": "your-dune-api-key-here"
     },
     "disabled": false
   }
   ```
   Alternatively, if you prefer running from source:
   ```json
   {
     "name": "spice-mcp", 
     "command": "python",
     "args": ["-m", "spice_mcp.mcp.server"],
     "env": {
       "PYTHONPATH": "/path/to/your/spice-mcp/src",
       "DUNE_API_KEY": "your-dune-api-key-here"
     },
     "disabled": false
   }
   ```

3. **Restart Cursor** to load the MCP server

4. **Verify Connection**:
   - Open Cursor and use the command palette (Cmd/Ctrl + Shift + P)
   - Search for "MCP" or "spice" commands
   - Test with `dune_health_check` to verify the connection

5. **Available Tools in Cursor**:
   - `dune_query`: Run Dune queries by ID, URL, or raw SQL
   - `dune_find_tables`: Search schemas and list tables
   - `dune_describe_table`: Get column metadata
   - `sui_package_overview`: Analyze Sui packages
   - `dune_health_check`: Verify API connection

**Tip**: Create a `.env` file in your project root with `DUNE_API_KEY=your-key-here` for easier configuration.

## MCP Tools and Features

All tools expose typed parameters, titles, and tags; failures return a consistent error envelope.

- `dune_query_info` (Query Info, tags: dune, query)
  - Fetch saved-query metadata by ID/URL (name, parameters, tags, SQL, version).

- `dune_query` (Run Dune Query, tags: dune, query)
  - Execute by ID/URL/raw SQL with parameters. Supports `refresh`, `max_age`, `limit/offset`, `sample_count`, `sort_by`, `columns`, and `format` = `preview|raw|metadata|poll`; accepts `timeout_seconds`.

- `dune_health_check` (Health Check, tag: health)
  - Checks API key presence, query-history path, logging enabled; best-effort template check when configured.

- `dune_find_tables` (Find Tables, tags: dune, schema)
  - Search schemas by keyword and/or list tables in a schema (`limit`).

- `dune_describe_table` (Describe Table, tags: dune, schema)
  - Column metadata for `schema.table` (Dune types + Polars inferred dtypes when available).

- `sui_package_overview` (Sui Package Overview, tag: sui)
  - Compact Sui activity overview for `packages[]` with `hours` (default 72) and `timeout_seconds`.

- Dune Admin tools (tags: dune, admin)
  - `dune_query_create(name, query_sql, description?, tags?, parameters?)`
  - `dune_query_update(query_id, name?, query_sql?, description?, tags?, parameters?)`
  - `dune_query_fork(source_query_id, name?)`

### Resources
- `spice:history/tail/{n}` — tail last N lines of query history (1..1000)
- `spice:artifact/{sha}` — fetch stored SQL by 64-hex SHA-256
- `spice:sui/events_preview/{hours}/{limit}/{packages}` — Sui events preview (JSON)
- `spice:sui/package_overview/{hours}/{timeout_seconds}/{packages}` — Sui overview (JSON)

## Resources

- `spice:history/tail/{n}`
  - Last `n` lines from the query-history JSONL, clamped to [1, 1000]

- `spice:artifact/{sha}`
  - Returns stored SQL for the SHA-256 (validated as 64 lowercase hex)

Tests
- Offline/unit tests (no network) live under `tests/offline/` and `tests/http_stubbed/`.
- Live tests under `tests/live/` are skipped by default; enable with `SPICE_TEST_LIVE=1` and a valid `DUNE_API_KEY`.
- Comprehensive scripted runner (tiered):
  - Run all tiers: `python tests/scripts/comprehensive_test_runner.py`
  - Select tiers: `python tests/scripts/comprehensive_test_runner.py -t 1 -t 3`
  - Stop on first failure: `python tests/scripts/comprehensive_test_runner.py --stop`
  - Optional JUnit export: `python tests/scripts/comprehensive_test_runner.py --junit tests/scripts/report.xml`
- Pytest directly (offline/default): `uv run pytest -q -m "not live" --cov=src/spice_mcp --cov-report=term-missing`

Core Tools (with parameters)
- `dune_query`
  - Use: Preview/query results by ID, URL, or raw SQL (Polars preview + Dune metadata/pagination).
  - Params: `query` (string), `parameters?` (object), `performance?` ('medium'|'large'), `limit?` (int), `offset?` (int), `sort_by?` (string), `columns?` (string[]), `sample_count?` (int), `refresh?` (bool), `max_age?` (number), `timeout_seconds?` (number), `format?` ('preview'|'raw'|'metadata').
  - Output: `type`, `rowcount`, `columns`, `data_preview`, `execution_id`, `duration_ms`, `metadata?`, `next_uri?`, `next_offset?`.
- `dune_find_tables`
  - Use: Search schemas by keyword and/or list tables for a schema.
  - Params: `keyword?` (string), `schema?` (string), `limit?` (int)
  - Output: `schemas?` (string[]), `tables?` (string[])
- `dune_describe_table`
  - Use: Column descriptions for `schema.table` via SHOW + fallback to 1-row sample inference.
  - Params: `schema` (string), `table` (string)
  - Output: `columns` ([{ name, dune_type?, polars_dtype?, extra?, comment? }])
- `sui_package_overview`
  - Use: Small-window overview for Sui packages (events/transactions/objects) with timeout handling.
  - Params: `packages` (string[]), `hours?` (int, default 72), `timeout_seconds?` (number, default 30)
  - Output: best-effort counts and previews; may include `*_timeout`/`*_error`
- `dune_health_check`
  - Use: Verify API key presence and logging paths
  - Output: `api_key_present`, `query_history_path`, `logging_enabled`, `status`

## Docs
- See [docs/index.md](docs/index.md) for full documentation:
  - Dune API structure and capabilities: [docs/dune_api.md](docs/dune_api.md)
  - Discovery patterns and examples: [docs/discovery.md](docs/discovery.md)
  - Sui package workflows: [docs/sui_packages.md](docs/sui_packages.md)
  - Tool reference and schemas: [docs/tools.md](docs/tools.md)
  - Codex CLI + tooling integration: [docs/codex_cli.md](docs/codex_cli.md), [docs/codex_cli_tools.md](docs/codex_cli_tools.md)
  - Architecture overview: [docs/architecture.md](docs/architecture.md)
  - Installation and configuration: [docs/installation.md](docs/installation.md), [docs/config.md](docs/config.md)
  - Development and linting: [docs/development.md](docs/development.md)

Notes
- Legacy Spice code now lives under `src/spice_mcp/adapters/dune` (extract, cache, urls, types).
- Ports and models live in `src/spice_mcp/core`; services consume ports and are exercised by FastMCP tools.
- Query history and SQL artefacts are always-on (see `src/spice_mcp/logging/query_history.py`).
- To bypass dot-env loading during tests/CI, export `SPICE_MCP_SKIP_DOTENV=1`.
- LazyFrames everywhere: eager `.collect()` or `pl.DataFrame` usage outside dedicated helpers is blocked by `tests/style/test_polars_lazy.py`; materialization helpers live in `src/spice_mcp/polars_utils.py`.
