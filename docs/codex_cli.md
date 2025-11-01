Codex CLI MCP Setup (spice_mcp_beta)

Goal
- Register the spice-mcp server as an MCP provider named `spice_mcp_beta` for Codex CLI, so you can call tools like `dune_query`.

Prereqs
- Dune API key in your shell (e.g., export `DUNE_API_KEY=...`)
- Python 3.9+; this repo checked out at `/Users/evandekim/Documents/spice_mcp`

Install (optional)
- `uv pip install -e .` (or `pip install -e .`) — optional; not required if using PYTHONPATH with `python -m`.

Register MCP server
- Option A (session‑local, recommended): do not write any config; pass everything via -c overrides and inherit the API key from your shell

```
export DUNE_API_KEY=YOUR_KEY
codex -C /Users/evandekim/Documents/spice_mcp \
  -c 'mcp_servers=["spice_mcp_beta"]' \
  -c 'mcp_servers.spice_mcp_beta.command="python"' \
  -c 'mcp_servers.spice_mcp_beta.args=["-m","spice_mcp.mcp.server"]' \
  -c 'mcp_servers.spice_mcp_beta.env={"PYTHONPATH":"/Users/evandekim/Documents/spice_mcp/src"}' \
  -c 'shell_environment_policy.inherit=["DUNE_API_KEY"]'
```

- Option B: write a global entry without secrets (you may need to grant Codex permissions to edit `~/.codex/config.toml`)

```
codex mcp add spice_mcp_beta python -m spice_mcp.mcp.server --env PYTHONPATH=/Users/evandekim/Documents/spice_mcp/src
```

Then always launch Codex inheriting the API key (no secrets stored in config):

```
export DUNE_API_KEY=YOUR_KEY
codex -C /Users/evandekim/Documents/spice_mcp -c 'mcp_servers=["spice_mcp_beta"]' -c 'shell_environment_policy.inherit=["DUNE_API_KEY"]'
```

- Option C: use installed console script if available on PATH (no secrets stored)

```
codex mcp add spice_mcp_beta spice-mcp

export DUNE_API_KEY=YOUR_KEY
codex -C /Users/evandekim/Documents/spice_mcp -c 'mcp_servers=["spice_mcp_beta"]' -c 'shell_environment_policy.inherit=["DUNE_API_KEY"]'
```

Update or remove server
- To update (e.g., new args):
  - `codex mcp remove spice_mcp_beta`
  - `codex mcp add spice_mcp_beta python -m spice_mcp.mcp.server --env PYTHONPATH=/Users/evandekim/Documents/spice_mcp/src`

Verify configuration
- `codex mcp list` should list `spice_mcp_beta` with the python command and no secrets in Env.

Try some tools
- Find schemas and tables
  - `mcp__spice_mcp_beta__dune_discover {"keyword": "dex", "source": "dune"}`
- Describe a table
  - `mcp__spice_mcp_beta__dune_describe_table {"schema": "dex", "table": "trades"}`
- Query preview (with metadata/pagination)
  - `mcp__spice_mcp_beta__dune_query {"query": "4388", "limit": 5}`
  - `mcp__spice_mcp_beta__dune_query {"query": "SELECT * FROM dex.trades LIMIT 5"}`

Notes & troubleshooting
- Secret safety: Never store `DUNE_API_KEY` in Codex config; use `shell_environment_policy.inherit=["DUNE_API_KEY"]` or set it in your shell.
- Missing key error: If you see `DUNE_API_KEY required`, export it in your shell and relaunch. The server also attempts to load `.env` from the project or home directory as a fallback.
- FastMCP stdout: This server disables FastMCP banners/logging to keep stdio clean; if handshakes fail, ensure you used the exact `python -m spice_mcp.mcp.server` and PYTHONPATH as shown.
- Heavy scans: Start with `format="metadata"` on `dune_query`, use `performance="large"`, and small `limit` with a recent time window.
- Tests/CI: set `SPICE_MCP_SKIP_DOTENV=1` to stop `_ensure_initialized` from reading local `.env` files when the key is intentionally absent.
