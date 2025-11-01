Tools Reference

All tools are exposed by the MCP server started with `spice-mcp`.

1) dune_query
- Purpose: Execute Dune queries (ID, URL, raw SQL) and return a compact preview plus Dune metadata/pagination hints.
- Input schema:
  - query: string (required)
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

Examples
- Preview latest metadata without rows:
  - `dune_query {"query":"4388","format":"metadata"}`
- Preview first rows and metadata:
  - `dune_query {"query":"4388","limit":10}`

Logging & Artifacts
- Successful calls are written to a JSONL audit log (see `docs/config.md` for path configuration via `QueryHistory`).
- The canonical SQL is stored as a deduplicated artefact keyed by SHA‑256 (for raw SQL and query IDs/URLs), enabling reproducibility and offline review.
- Result caching is handled by `adapters.dune.cache` (parquet files) and can be tuned via `SPICE_CACHE_*` environment variables.
 

2) dune_find_tables
- Purpose: Search schemas by keyword and/or list tables in a schema.
- Input schema:
 - keyword?: string — search pattern for schema names
  - schema?: string — schema to list tables from
  - limit?: integer (default 50)
- Output fields:
  - schemas?: string[]
  - tables?: string[]
  - Errors follow the standard MCP envelope.

3) dune_describe_table
- Purpose: Describe columns for a schema.table (SHOW + fallback to 1-row SELECT inference).
- Input schema:
  - schema: string
  - table: string
- Output fields:
  - columns: [{ name, dune_type?, polars_dtype?, extra?, comment? }]
  - Errors follow the standard MCP envelope.

4) sui_package_overview
- Purpose: Preview Sui package activity (events, transactions, objects) over a time window; timeouts supported.
- Input schema:
  - packages: string[] (required)
  - hours?: integer (default 72)
  - timeout_seconds?: number (default 30)
- Output fields (best-effort):
  - ok: boolean
  - events_count?, events_preview?, events_timeout?, events_error?
  - transactions_count?, transactions_preview?, transactions_timeout?, transactions_error?
  - objects_count?, objects_preview?, objects_timeout?, objects_error?
  - On error: { ok: false, error: { … } }

 5) dune_health_check
- Purpose: Basic environment and logging readiness check.
- Output fields: ok, api_key_present, status

6) dune_query_info
- Purpose: Fetch Dune query object metadata (name, description, tags, parameter schema, SQL).
- Input schema:
  - query: string — ID or URL
- Output fields:
  - ok: boolean, status: number, query_id: number
  - name?: string, description?: string, tags?: string[], parameters?: object[], version?: number, query_sql?: string

7) dune_query_create
- Purpose: Create a saved Dune query.
- Input schema:
  - name: string (required)
  - query_sql: string (required)
  - description?: string, tags?: string[], parameters?: object[]
- Output: Dune query object

8) dune_query_update
- Purpose: Update a saved Dune query.
- Input schema:
  - query_id: integer (required)
  - name?: string, query_sql?: string, description?: string, tags?: string[], parameters?: object[]
- Output: Dune query object

9) dune_query_fork
- Purpose: Fork an existing saved Dune query.
- Input schema:
  - source_query_id: integer (required)
  - name?: string (new name)
- Output: Dune query object
