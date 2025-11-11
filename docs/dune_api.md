Dune API Overview

Endpoints
- Query metadata: `GET /api/v1/query/{id}`
  - name, description, tags, version, parameters (types, defaults), query_sql
- Execute query: `POST /api/v1/query/{id}/execute`
  - body: { query_parameters?: object, performance?: 'medium'|'large' }
  - returns: { execution_id }
- Execution status: `GET /api/v1/execution/{execution_id}/status`
  - fields: is_execution_finished, state, execution_started_at, execution_ended_at
- Results (JSON): `GET /api/v1/query/{id}/results?limit=&offset=&sort_by=&columns=&sample_count=`
  - top-level: execution_id, is_execution_finished, state, submitted_at, expires_at, execution_started_at, execution_ended_at
  - result.rows[]: array of objects
  - result.metadata: { column_names[], column_types[], row_count, total_row_count, ... }
  - pagination: next_uri, next_offset (when more rows available)
- Results (CSV): `GET /api/v1/query/{id}/results/csv?...`
  - pagination headers: `x-dune-next-uri`, `x-dune-next-offset`, `Link: rel="next"`

Parameters
- query_parameters: object — pass SQL parameters defined in the query (text/number/datetime/enum)
- performance: 'medium' | 'large' — server-side execution hint
- limit, offset: row paging; sample_count: random sample of rows; sort_by, columns: server-side projection and ordering

Status & Errors
- Poll status until is_execution_finished or failure state (QUERY_STATE_FAILED)
- Rate limiting: HTTP 429 with backoff recommended
- No latest execution: JSON error message indicates none exists for latest version

Metadata-First Planning
- Use JSON results endpoint with limit=0 to fetch `result.metadata` quickly (row counts and column names/types) before fetching data.

Raw SQL Support
- By default, spice-mcp uses Dune's Execute SQL endpoint (`POST /api/v1/execution/sql`) for raw SQL queries. This provides cleaner execution IDs and avoids template query dependencies.
- Legacy template-based execution is available via `SPICE_DUNE_RAW_SQL_ENGINE=template` for backward compatibility.
- Execute SQL endpoint: `POST /api/v1/execution/sql` with body `{query_sql, parameters?, timeout_seconds?}` returns `{execution_id}`. Poll status and fetch results using standard execution endpoints.

Admin Operations
- Archive query: `POST /api/v1/query/{id}/archive`
- Unarchive query: `POST /api/v1/query/{id}/unarchive`
- These operations are exposed via MCP tools `dune_query_archive` and `dune_query_unarchive`. See docs/tools.md for parameters.

Safe Mode
- By default, saved-query tools (`dune_query_create`, `dune_query_update`, `dune_query_fork`) are disabled to prevent accidental query persistence.
- Enable with `SPICE_DUNE_ALLOW_SAVES=true` in your environment.
- Use `dune_query` for ad-hoc analysis (no persistence). Use `dune_query_create` only when you explicitly want to save queries.
- Created queries are automatically tagged with `['spice-mcp']` for easy filtering and cleanup.
- Optionally force queries to be private with `SPICE_DUNE_FORCE_PRIVATE=true`.
- Query history logs are saved to `logs/queries.jsonl` (repo) or `~/.spice_mcp/logs/queries.jsonl` (home). Use `scripts/dune_collect_query_ids.py` to extract query IDs for bulk operations.
- Bulk archive/unarchive: Use `scripts/dune_bulk_archive.py` with collected query IDs. See `scripts/README.md` for usage.

Audit Logging
- All query executions and admin operations are recorded to a JSONL history (path configurable via environment). Admin operations are logged with `action_type="admin_action"` and include the `query_id` for traceability.
- Raw SQL executions using Execute SQL endpoint log only `execution_id` (no `template_query_id`).

Admin Operations
- Archive query: `POST /api/v1/query/{id}/archive`
- Unarchive query: `POST /api/v1/query/{id}/unarchive`
- These operations are exposed via MCP tools `dune_query_archive` and `dune_query_unarchive`. See docs/tools.md for parameters.

Audit Logging
- All query executions and admin operations are recorded to a JSONL history (path configurable via environment). Admin operations are logged with `action_type="admin_action"` and include the `query_id` for traceability.

