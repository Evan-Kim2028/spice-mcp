Installation

Prerequisites
- Python 3.9+
- A Dune API key (`DUNE_API_KEY`)

Install
- From source: `uv pip install .` (or `pip install .`)

Run MCP Server
- `spice-mcp` (stdio server)

Environment
- Required: `DUNE_API_KEY`
- Optional:
  - `SPICE_CACHE_MODE` = enabled | read_only | refresh | disabled
  - `SPICE_CACHE_DIR` = directory for local parquet caching
  - `SPICE_QUERY_HISTORY` = JSONL path for audit log (or `disabled`)
  - `SPICE_ARTIFACT_ROOT` = base path for artifacts (SQL, results)
  - `SPICE_TIMEOUT_SECONDS` = default polling timeout (seconds)

