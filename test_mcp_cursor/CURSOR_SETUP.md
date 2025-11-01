# Cursor MCP Setup Instructions

## Step-by-Step Setup

### 1. Install spice-mcp from Source

```bash
cd /Users/evandekim/Documents/spice_mcp
uv pip install -e .
```

This installs the latest code with Issue #8 fixes.

### 2. Set Up Environment Variables

Create or edit `test_mcp_cursor/.env`:

```bash
DUNE_API_KEY=your-actual-api-key-here
```

Get your API key from: https://dune.com/settings/api

### 3. Configure Cursor MCP

In Cursor IDE:

1. Open Settings (Cmd+, on Mac, Ctrl+, on Windows/Linux)
2. Search for "MCP Servers" or navigate to **Features → MCP Servers**
3. Click "Edit in settings.json" or add configuration manually

Add this configuration:

```json
{
  "mcpServers": {
    "spice-mcp": {
      "command": "spice-mcp",
      "env": {
        "DUNE_API_KEY": "your-actual-api-key-here"
      }
    }
  }
}
```

**OR** use the file path method (recommended for testing):

```json
{
  "mcpServers": {
    "spice-mcp": {
      "command": "spice-mcp",
      "env": {
        "DUNE_API_KEY": "${DUNE_API_KEY}"
      }
    }
  }
}
```

And set the environment variable in your shell before starting Cursor.

### 4. Restart Cursor

After adding the MCP server configuration, restart Cursor IDE completely.

### 5. Verify Connection

1. Open Cursor's MCP panel (usually accessible via command palette: Cmd+Shift+P → "MCP")
2. Check that `spice-mcp` appears in the list
3. Run a health check:
   - Use Cursor's chat interface
   - Ask: "Run dune_health_check"
   - Should return status confirming API key is present

### 6. Test Issue #8 Fixes

Run the test script:

```bash
cd /Users/evandekim/Documents/spice_mcp
python test_mcp_cursor/test_issue_8_scenarios.py
```

Or test manually in Cursor:

1. **Test 1: Query with no parameters**
   ```
   Run dune_query with query="SELECT 'test' as status" and format="preview"
   ```

2. **Test 2: Query with parameters=None**
   ```
   Run dune_query with query="SELECT 1" and parameters=null
   ```

3. **Test 3: Raw SQL query**
   ```
   Run dune_query with query="SELECT schema_name FROM information_schema.schemata LIMIT 5"
   ```

All should work without "overloaded function" errors.

## Troubleshooting

### "spice-mcp command not found"

Make sure you installed with `uv pip install -e .` and that your PATH includes the Python environment.

### "Overloaded function error" still appears

1. Verify you installed from source: `uv pip list | grep spice-mcp`
2. Check the version matches the repo
3. Restart Cursor completely
4. Check Cursor's MCP logs for errors

### "404 errors" on discovery tools

- Verify your API key is valid
- Check that the template query (4060379) is accessible
- Ensure you have network access to Dune API

### MCP Server not appearing in Cursor

1. Check Cursor's MCP logs (usually in View → Output → MCP)
2. Verify JSON syntax in settings.json
3. Make sure `spice-mcp` command is in PATH
4. Try absolute path: `"command": "/full/path/to/.venv/bin/spice-mcp"`

## Verification Checklist

- [ ] spice-mcp installed from source (`uv pip install -e .`)
- [ ] `.env` file has valid DUNE_API_KEY
- [ ] Cursor MCP configuration added to settings.json
- [ ] Cursor restarted after configuration
- [ ] `dune_health_check` works in Cursor
- [ ] `dune_query` works without parameters
- [ ] `dune_query` works with parameters=None
- [ ] Raw SQL queries execute successfully
- [ ] No "overloaded function" errors

## Expected Behavior After Fix

✅ All query types work:
- Query IDs: `dune_query(query="4388")`
- URLs: `dune_query(query="https://dune.com/queries/4388")`
- Raw SQL: `dune_query(query="SELECT 1")`

✅ Parameters handled correctly:
- `parameters=None` works
- `parameters={"key": "value"}` works
- Missing `parameters` keyword defaults to None

✅ No errors:
- No "overloaded function" errors
- No "Parameter must be object, got string" errors
- Proper error messages for actual failures

