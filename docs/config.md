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
- Raw SQL
  - `SPICE_RAW_SQL_QUERY_ID`: ID of the template query used to execute raw SQL (default: 4060379). Health is reported by `dune_health_check` when set.

Programmatic
- See `src/spice_mcp/config.py` for the typed configuration model and env loading.
