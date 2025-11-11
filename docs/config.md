Configuration

Required
- `DUNE_API_KEY` — your Dune API key. Obtain from Dune settings.
 - `DUNE_API_URL` — override API base (default: https://api.dune.com/api/v1)

Optional
- Cache
  - `SPICE_CACHE_MODE`: enabled | read_only | refresh | disabled (default: enabled)
  - `SPICE_CACHE_DIR`: override cache location
  - `SPICE_CACHE_MAX_SIZE_MB`: advisory max cache size (default: 500)
- Logging
  - `SPICE_QUERY_HISTORY`: JSONL path for audit trail (or `disabled`)
  - `SPICE_ARTIFACT_ROOT`: base for artifacts (queries, results)
  - `SPICE_LOGGING_ENABLED`: true/false (default: true)
- Timeouts
  - `SPICE_TIMEOUT_SECONDS`: default polling timeout (seconds)
  - `SPICE_MAX_CONCURRENT_QUERIES`: reserved for future concurrency control (default: 5, not currently enforced)
- Query Safety (Safe Mode)
  - `SPICE_DUNE_ALLOW_SAVES`: Enable saved-query tools (create/update/fork). Default: `false`. Set to `true` to enable saving queries.
  - `SPICE_DUNE_FORCE_PRIVATE`: Force all created queries to be private. Default: `false`. Set to `true` to make queries private by default.
- Raw SQL
  - `SPICE_DUNE_RAW_SQL_ENGINE`: Execution engine for raw SQL. Options: `execution_sql` (default, uses POST /execution/sql) or `template` (legacy, uses template query ID).
  - `SPICE_RAW_SQL_QUERY_ID`: ID of the template query used when `SPICE_DUNE_RAW_SQL_ENGINE=template` (default: 4060379). Health is reported by `dune_health_check` when set.

Programmatic
- See `src/spice_mcp/config.py` for the typed configuration model and env loading.
