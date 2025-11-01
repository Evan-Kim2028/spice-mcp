Catalog Discovery

Summary
- There is no public REST endpoint to browse the full catalog. Discovery is best achieved using Dune SQL primitives and fallback probes.

Approach
- Schemas
  - SHOW SCHEMAS
  - SHOW SCHEMAS LIKE '%keyword%'
- Tables
  - SHOW TABLES FROM <schema>
  - If SHOW is blocked, probe candidate names via SELECT 1 FROM <schema>.<table> LIMIT 1
- Columns
  - SHOW COLUMNS FROM <schema>.<table>
  - Fallback: SELECT * FROM <schema>.<table> LIMIT 1, infer columns and Polars dtypes client-side
- INFORMATION_SCHEMA
  - Some deployments allow: information_schema.schemata/tables/columns
  - If blocked, use SHOW + probes


Helpers in this repo
- `src/spice_mcp/service_layer/discovery_service.py` provides service wrappers around the Dune adapter:
  - `find_schemas(keyword)`, `list_tables(schema, limit)`, `describe_table(schema, table)`

MCP Tools
- dune_find_tables: search schemas and list tables
- dune_describe_table: describe columns with SHOW + fallback
