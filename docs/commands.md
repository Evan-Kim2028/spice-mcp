MCP Command URIs

These command-style resources are backed by `SuiService` (service layer) and provide lightweight, default-bounded previews for Sui data. They are intended for quick, safe exploration during development. For most workloads, prefer the `dune_query` tool.

General Notes
- These are MCP “resources” (URIs), not standard tools. Use your client’s “read resource” capability.
- Responses are JSON strings (serialized). Parse the returned string to consume fields like `ok`, `rowcount`, and `data_preview`.
- Defaults are tuned to avoid heavy scans (3-day window, small LIMITs).

1) Sui Events Preview
- URI: `spice:sui/events_preview/{hours}/{limit}/{packages}`
  - `hours`: integer, default 72 (3 days) if malformed
  - `limit`: integer, default 50 if malformed
  - `packages`: comma-separated 0x addresses; use `_` for “no filter”
- Behavior
  - Filters by `lower(event_type) LIKE '0x<package>::%'` (avoids ILIKE grammar issues)
  - Applies time window and LIMIT; uses `performance='large'` under the hood
- Returns (JSON string)
  - `{ "ok": true, "rowcount": number, "columns": string[], "data_preview": object[] }`
  - On error: `{ "ok": false, "error": { code, message, data: { suggestions }, context? } }`
- Examples
  - `spice:sui/events_preview/72/50/0xcaf6...,0x2c8d...`
  - `spice:sui/events_preview/72/50/_` (no packages filter)

2) Sui Package Overview (Command)
- URI: `spice:sui/package_overview/{hours}/{timeout_seconds}/{packages}`
  - `hours`: integer, default 72 (3 days) if malformed
  - `timeout_seconds`: number, default 30 if malformed
  - `packages`: comma-separated 0x addresses; required (use `_` for empty)
- Behavior
  - Computes best-effort previews for events, transactions, and objects touched by those packages
  - Applies efficient LIMITs and uses `performance='large'`
- Returns (JSON string)
  - `{ "ok": true, "events_preview"?: object[], "events_count"?: number, "transactions_preview"?: object[], "transactions_count"?: number, "objects_preview"?: object[], "objects_count"?: number, "events_timeout"?: true, "transactions_timeout"?: true, "objects_timeout"?: true }`
  - On error: `{ "ok": false, "error": { … } }`
- Examples
  - `spice:sui/package_overview/72/30/0xcaf6...,0x2c8d...`

When to use
- Use these URIs for quick, bounded previews to reduce timeouts and cost during discovery.
- Once you know what you want, switch to `dune_query` for precise, parameterized queries (and use `format="metadata"` first to inspect shape and row counts).
