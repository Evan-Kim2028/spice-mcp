Codex CLI MCP Setup (spice_mcp_beta)

Goal
- Register the spice-mcp server as an MCP provider named `spice_mcp_beta` for Codex CLI, so you can call tools like `dune_query` and use the Sui command URIs.

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
- Find Sui schemas
  - `mcp__spice_mcp_beta__dune_find_tables {"keyword": "sui"}`
- Describe `sui.transactions`
  - `mcp__spice_mcp_beta__dune_describe_table {"schema": "sui", "table": "transactions"}`
- Query preview (with metadata/pagination)
  - `mcp__spice_mcp_beta__dune_query {"query": "4388", "limit": 5}`
  - `mcp__spice_mcp_beta__dune_query {"query": "SELECT * FROM sui.events LIMIT 5"}`
MCP command URIs (resources)
- You can read command-style resources for safe defaults (3-day windows, small LIMITs):
  - Events preview: `spice:sui/events_preview/72/50/0xcaf6...,0x2c8d...`
  - Package overview (cmd): `spice:sui/package_overview/72/30/0xcaf6...,0x2c8d...`
  - Global preview (no package filter): `spice:sui/events_preview/72/50/_`
  - See `docs/commands.md` for details. (Your client must support reading MCP resources.)

Notes & troubleshooting
- Secret safety: Never store `DUNE_API_KEY` in Codex config; use `shell_environment_policy.inherit=["DUNE_API_KEY"]` or set it in your shell.
- Missing key error: If you see `DUNE_API_KEY required`, export it in your shell and relaunch. The server also attempts to load `.env` from the project or home directory as a fallback.
- FastMCP stdout: This server disables FastMCP banners/logging to keep stdio clean; if handshakes fail, ensure you used the exact `python -m spice_mcp.mcp.server` and PYTHONPATH as shown.
- Heavy scans: Start with `format="metadata"` on `dune_query`, use `performance="large"`, and small `limit` with a recent time window; the Sui command URIs default to safe windows and limits.
- Tests/CI: set `SPICE_MCP_SKIP_DOTENV=1` to stop `_ensure_initialized` from reading local `.env` files when the key is intentionally absent.
