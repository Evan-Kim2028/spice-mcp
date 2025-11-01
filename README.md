# spice-mcp

[![PyPI version](https://img.shields.io/pypi/v/spice-mcp.svg)](https://pypi.org/project/spice-mcp/)
<a href="https://glama.ai/mcp/servers/@Evan-Kim2028/spice-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@Evan-Kim2028/spice-mcp/badge" alt="Spice MCP server" />
</a>

An MCP server that provides AI agents with direct access to [Dune Analytics](https://dune.com/) data. Execute queries, discover schemas and tables, and manage saved queries—all through a clean, type-safe interface optimized for AI workflows.

**Discover High-Quality Tables**: Leverages [Dune Spellbook](https://github.com/duneanalytics/spellbook), Dune's official GitHub repository of curated dbt models, to surface verified, production-ready tables with rich metadata.

## Why spice-mcp?

- **Agent-friendly**: Designed for AI agents using the Model Context Protocol (MCP)
- **High-Quality Discovery**: Leverages Dune Spellbook's GitHub repository to find verified, production-ready tables with rich metadata
- **Efficient**: Polars-first pipeline keeps data lazy until needed, reducing memory usage
- **Discovery**: Built-in tools to explore Dune's extensive blockchain datasets from both Dune API and Spellbook
- **Type-safe**: Fully typed parameters and responses with FastMCP
- **Reproducible**: Automatic query history logging and SQL artifact storage

## Quick Start

1. **Install**:
   ```bash
   uv pip install spice-mcp
   ```

2. **Set API key** (choose one method):
   - **Option A**: Create a `.env` file in your project root:
     ```bash
     echo "DUNE_API_KEY=your-api-key-here" > .env
     ```
   - **Option B**: Export in your shell:
     ```bash
     export DUNE_API_KEY=your-api-key-here
     ```

3. **Use with Cursor IDE**:
   Add to Cursor Settings → MCP Servers:
   ```json
   {
     "name": "spice-mcp",
     "command": "spice-mcp",
     "env": {
       "DUNE_API_KEY": "your-dune-api-key-here"
     }
   }
   ```

**Note**: Query history logging is enabled by default. Logs are saved to `logs/queries.jsonl` (or `~/.spice_mcp/logs/queries.jsonl` if not in a project directory). To customize paths, set `SPICE_QUERY_HISTORY` and `SPICE_ARTIFACT_ROOT` environment variables.

## Core Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `dune_query` | Execute queries by ID, URL, or raw SQL | `query` (str), `parameters` (object), `limit` (int), `offset` (int), `format` (`preview\|raw\|metadata\|poll`), `refresh` (bool), `timeout_seconds` (float) |
| `dune_query_info` | Get metadata for a saved query | `query` (str - ID or URL) |
| `dune_discover` | Unified discovery across Dune API and Spellbook (returns verified tables only). **Leverages Dune Spellbook GitHub repository** for high-quality, curated tables. | `keyword` (str\|list), `schema` (str), `limit` (int), `source` (`dune\|spellbook\|both`), `include_columns` (bool) |
| `dune_describe_table` | Get column metadata for a table | `schema` (str), `table` (str) |
| `dune_health_check` | Verify API key and configuration | (no parameters) |
| `dune_query_create` | Create a new saved query | `name` (str), `query_sql` (str), `description` (str), `tags` (list), `parameters` (list) |
| `dune_query_update` | Update an existing saved query | `query_id` (int), `name` (str), `query_sql` (str), `description` (str), `tags` (list), `parameters` (list) |
| `dune_query_fork` | Fork an existing saved query | `source_query_id` (int), `name` (str) |

## Resources

- `spice:history/tail/{n}` — View last N lines of query history (1-1000)
- `spice:artifact/{sha}` — Retrieve stored SQL by SHA-256 hash

## What is Dune?

[Dune](https://dune.com/) is a crypto data platform providing curated blockchain datasets and a public API. It aggregates on-chain data from Ethereum, Solana, Polygon, and other chains into queryable SQL tables. See the [Dune Docs](https://dune.com/docs) for more information.

## What is Dune Spellbook?

[Dune Spellbook](https://github.com/duneanalytics/spellbook) is Dune's official GitHub repository containing thousands of curated dbt models. These models represent high-quality, production-ready tables that are:

- **Verified**: All tables are verified to exist in Dune before being returned
- **Well-documented**: Rich metadata including column descriptions and types
- **Maintained**: Regularly updated by the Dune community and team
- **Production-ready**: Used by analysts and dashboards across the ecosystem

spice-mcp automatically clones and parses the Spellbook repository to discover these high-quality tables, parsing dbt config blocks to resolve actual Dune table names and verifying their existence before returning them to you.

## Installation

**From PyPI** (recommended):
```bash
uv pip install spice-mcp
```

**From source**:
```bash
git clone https://github.com/Evan-Kim2028/spice-mcp.git
cd spice-mcp
uv sync
uv pip install -e .
```

**Requirements**: Python 3.13+

## Documentation

- [Tool Reference](docs/tools.md) — Complete tool documentation with parameters
- [Architecture](docs/architecture.md) — Code structure and design patterns
- [Discovery Guide](docs/discovery.md) — How to explore Dune schemas and tables
- [Dune API Guide](docs/dune_api.md) — Understanding Dune's data structure
- [Configuration](docs/config.md) — Environment variables and settings

## License

See [LICENSE](LICENSE) file for details.
