# Quick Start: Testing Issue #8 Fixes with Cursor MCP

## ✅ Current Status

All tests passing! The Issue #8 fixes are working correctly:
- ✅ FastMCP Registration
- ✅ Parameters=None accepted
- ✅ Parameters as dict accepted
- ✅ No parameters keyword works
- ✅ Raw SQL execution doesn't trigger overloaded function error

## Setup Steps

### 1. Install from Source (Required!)

```bash
cd /Users/evandekim/Documents/spice_mcp
uv pip install -e .
```

**IMPORTANT**: Don't use `uv pip install spice-mcp==0.1.3` - that installs from PyPI and doesn't have the fixes yet.

### 2. Verify Installation

```bash
uv pip list | grep spice-mcp
```

Should show:
```
spice-mcp    0.1.3    /Users/evandekim/Documents/spice_mcp
```

### 3. Set Up Environment

```bash
cd test_mcp_cursor
cp .env.example .env
# Edit .env and add your DUNE_API_KEY
```

### 4. Run Tests

```bash
cd /Users/evandekim/Documents/spice_mcp
python test_mcp_cursor/test_issue_8_scenarios.py
```

Expected output: `5/5 tests passed 🎉`

### 5. Configure Cursor MCP

Add to Cursor Settings → MCP Servers:

```json
{
  "mcpServers": {
    "spice-mcp": {
      "command": "spice-mcp",
      "env": {
        "DUNE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### 6. Test in Cursor

1. Restart Cursor completely
2. Open Cursor's chat interface
3. Try these commands:
   - `Run dune_health_check`
   - `Run dune_query with query="SELECT 'test' as status" and format="preview"`
   - `Run dune_query with query="SELECT 1" and parameters=null`

All should work without "overloaded function" errors!

## What Was Fixed

1. **Type annotations**: Changed from `dict[str, Any] | None` to `Optional[dict[str, Any]]` for FastMCP compatibility
2. **Parameter normalization**: Added defensive handling for edge cases
3. **FastMCP schema generation**: Now correctly generates JSON schemas that accept None

## Files Changed

- `src/spice_mcp/mcp/server.py` - Updated type annotations
- `tests/fastmcp/test_dune_query_schema_validation.py` - New integration tests
- `test_mcp_cursor/` - Complete test setup

## Next Steps

1. Test with actual Cursor MCP to verify end-to-end
2. If all works, prepare release (bump version, update changelog)
3. Release to PyPI as 0.1.4 (or appropriate version)

