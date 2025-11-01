Tools Reference

All tools are exposed by the MCP server started with `spice-mcp`.

1) dune_discover
- Purpose: **PRIMARY discovery tool** for finding tables in Dune. Searches both Dune API and Spellbook repository. Returns ONLY verified, queryable tables.
- ⚠️ **IMPORTANT**: Always use this tool instead of querying `information_schema` directly (which is slow and causes lag).
- Input schema:
  - keyword?: string | string[] — search term(s) to find schemas/tables (e.g., "walrus", ["layerzero", "dex"])
  - schema?: string — schema name to list tables from (e.g., "dex", "sui_walrus")
  - limit?: integer (default 50) — maximum number of tables to return
  - source?: 'dune' | 'spellbook' | 'both' (default 'both') — where to search
  - include_columns?: boolean (default true) — include column details for Spellbook models
- Output fields:
  - schemas: string[] — matching schema names
  - tables: array of table objects, each with:
    - schema: string — Spellbook subproject name (for Spellbook models) or Dune schema name
    - table: string — Spellbook model name (for Spellbook models) or Dune table name
    - fully_qualified_name: string — schema.table format
    - source: 'dune' | 'spellbook'
    - dune_schema?: string — actual Dune schema name (for Spellbook models, parsed from dbt config)
    - dune_alias?: string — actual Dune table alias (for Spellbook models, parsed from dbt config)
    - dune_table?: string — verified, queryable Dune table name (e.g., "sui_walrus.base_table")
    - verified?: boolean — true (all returned tables are verified to exist)
    - columns?: array — column details (if include_columns=true)
  - source: string — the source parameter used
  - message?: string — helpful message if no tables found
- Features:
  - Automatically parses dbt configs from Spellbook models to resolve actual Dune table names
  - Verifies tables exist in Dune before returning (uses persistent cache)
  - Filters out non-existent tables
- Examples:
  - Search for walrus tables (returns verified tables only):
    - `dune_discover {"keyword":"walrus"}`
    - → Returns tables with `dune_table` field like "sui_walrus.base_table"
  - Use discovered table to query:
    - `dune_query {"query":"SELECT * FROM sui_walrus.base_table LIMIT 10"}`
  - Search only Spellbook:
    - `dune_discover {"keyword":["layerzero","bridge"],"source":"spellbook"}`
  - List tables in a schema:
    - `dune_discover {"schema":"dex"}`

2) dune_query
- Purpose: Execute Dune queries (ID, URL, raw SQL) and return a compact preview plus Dune metadata/pagination hints.
- ⚠️ **IMPORTANT**: Always use `dune_discover` FIRST to find verified table names. Do not guess table names or query `information_schema` directly.
- Input schema:
  - query: string (required) — Query ID, URL, or raw SQL using tables from `dune_discover`
  - parameters?: object
  - performance?: 'medium' | 'large'
  - limit?: integer, offset?: integer, sort_by?: string, columns?: string[], sample_count?: integer
  - refresh?: boolean, max_age?: number, timeout_seconds?: number
  - format?: 'preview' | 'raw' | 'metadata' | 'poll' (preview by default)
  - extras?: object (e.g., allow_partial_results, ignore_max_datapoints_per_request)
- Output fields:
  - type: 'preview' | 'metadata' | 'raw' | 'execution'
  - rowcount: number, columns: string[]
  - data_preview: object[] (first rows)
  - execution_id: string, duration_ms: number
  - metadata?: structured Dune metadata / execution state / error hints
  - next_uri?: string, next_offset?: number
  - Errors: `{ "ok": false, "error": { code, message, data: { suggestions }, context? } }`
- Examples:
  - Workflow: discover → query:
    - `dune_discover {"keyword":"walrus"}` → get `dune_table="sui_walrus.base_table"`
    - `dune_query {"query":"SELECT * FROM sui_walrus.base_table LIMIT 10"}`
  - Preview latest metadata without rows:
    - `dune_query {"query":"4388","format":"metadata"}`
  - Preview first rows and metadata:
    - `dune_query {"query":"4388","limit":10}`

Logging & Artifacts
- Successful calls are written to a JSONL audit log (see `docs/config.md` for path configuration via `QueryHistory`).
- The canonical SQL is stored as a deduplicated artefact keyed by SHA‑256 (for raw SQL and query IDs/URLs), enabling reproducibility and offline review.
- Result caching is handled by `adapters.dune.cache` (parquet files) and can be tuned via `SPICE_CACHE_*` environment variables.
 

3) dune_describe_table
- Purpose: Describe columns for a schema.table (SHOW + fallback to 1-row SELECT inference).
- Input schema:
  - schema: string
  - table: string
- Output fields:
  - columns: [{ name, dune_type?, polars_dtype?, extra?, comment? }]
  - Errors follow the standard MCP envelope.

3) dune_health_check
- Purpose: Basic environment and logging readiness check.
- Output fields: ok, api_key_present, status

4) dune_query_info
- Purpose: Fetch Dune query object metadata (name, description, tags, parameter schema, SQL).
- Input schema:
  - query: string — ID or URL
- Output fields:
  - ok: boolean, status: number, query_id: number
  - name?: string, description?: string, tags?: string[], parameters?: object[], version?: number, query_sql?: string

5) dune_query_create
- Purpose: Create a saved Dune query.
- Input schema:
  - name: string (required)
  - query_sql: string (required)
  - description?: string, tags?: string[], parameters?: object[]
- Output: Dune query object

6) dune_query_update
- Purpose: Update a saved Dune query.
- Input schema:
  - query_id: integer (required)
  - name?: string, query_sql?: string, description?: string, tags?: string[], parameters?: object[]
- Output: Dune query object

7) dune_query_fork
- Purpose: Fork an existing saved Dune query.
- Input schema:
  - source_query_id: integer (required)
  - name?: string (new name)
- Output: Dune query object
