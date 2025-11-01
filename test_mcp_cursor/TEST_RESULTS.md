# Real API Test Results

## Test Environment
- API Key: Loaded from `.env` (masked in output)
- Template Query: 4060379 exists and is accessible
- Date: Testing Issue #8 fixes

## Issues Found

### 1. Overloaded Function Error (Partial Fix)
- ✅ **FIXED**: When `parameters=None` is explicitly passed
- ❌ **STILL FAILING**: When `parameters` keyword is omitted entirely
- **Root Cause**: FastMCP detects overloads in `extract.query()` during function inspection when optional parameters are omitted
- **Workaround**: Always pass `parameters=None` explicitly in MCP client calls

### 2. 404 Errors on Discovery Tools (Still Failing)
- ❌ `dune_find_tables` with keyword search returns 404
- ❌ `dune_discover` with keyword search returns 404  
- ❌ Raw SQL queries via template return 404
- **Root Cause**: `get_results()` is called with `query_id` and `parameters` before the query is executed. The URL tries to GET results that don't exist yet.
- **Location**: `src/spice_mcp/adapters/dune/extract.py` line 305
- **Expected Flow**: 
  1. Execute query (POST with parameters)
  2. Poll for completion
  3. GET results

### 3. Successful Tests
- ✅ `dune_query` with `parameters=None` works
- ✅ `dune_describe_table` works (has different error, not 404)

## Next Steps

1. **Fix overloaded function error**: Need to prevent FastMCP from detecting overloads when parameters keyword is omitted
   - Possible solution: Ensure FastMCP only sees the function signature, not imported functions
   - Or: Always require `parameters` keyword (breaking change)

2. **Fix 404 errors**: Modify `extract.query()` to execute query before trying to GET results
   - When `refresh=False` and `max_age` is not set, it tries to GET existing results
   - For parameterized queries (template query), those results might not exist
   - Should execute query first, then GET results

3. **Test with Cursor MCP**: Verify fixes work end-to-end with actual MCP client

## Template Query Details
- Query ID: 4060379
- Name: `run_dynamic_queries`
- Status: ✅ Accessible (200 OK)
- Has parameter: `query` (text type)
- Parameter format: `{"query": "SELECT ..."}`

