Catalog Discovery

Summary
- There is no public REST endpoint to browse the full catalog. Discovery is best achieved using Dune SQL primitives and fallback probes.
- **Native SHOW statements are preferred** - they're faster than information_schema queries. See issue #10 for details.

Approach
- Schemas
  - SHOW SCHEMAS
  - SHOW SCHEMAS LIKE '%keyword%'
  - ⚠️ Avoid: information_schema.schemata (slower, causes lag)
- Tables
  - SHOW TABLES FROM <schema>
  - If SHOW is blocked, probe candidate names via SELECT 1 FROM <schema>.<table> LIMIT 1
  - ⚠️ Avoid: information_schema.tables (slower, causes lag)
- Columns
  - SHOW COLUMNS FROM <schema>.<table>
  - Fallback: SELECT * FROM <schema>.<table> LIMIT 1, infer columns and Polars dtypes client-side
- INFORMATION_SCHEMA (Deprecated)
  - Previously used for portability, but causes performance issues
  - Native SHOW statements are now used directly (faster, no lag)
  - Kept as fallback only if SHOW is blocked


Helpers in this repo
- `src/spice_mcp/service_layer/discovery_service.py` provides service wrappers around the Dune adapter:
  - `find_schemas(keyword)`, `list_tables(schema, limit)`, `describe_table(schema, table)`

MCP Tools
- dune_discover: **PRIMARY discovery tool** - unified search across Dune API and Spellbook, returns verified tables only
  - Automatically parses dbt configs from Spellbook models to resolve actual Dune table names
  - Verifies tables exist in Dune before returning (uses persistent cache)
  - Filters out non-existent tables
- dune_describe_table: describe columns with SHOW + fallback
