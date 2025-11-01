# Cursor MCP Test Setup for Issue #8 Fix

This directory contains a fresh test setup to verify that the Issue #8 fixes work correctly with Cursor MCP.

## Setup Steps

1. **Install spice-mcp from local source**:
   ```bash
   cd /Users/evandekim/Documents/spice_mcp
   uv pip install -e .
   ```

2. **Create .env file** with your Dune API key:
   ```bash
   echo "DUNE_API_KEY=your-api-key-here" > test_mcp_cursor/.env
   ```

3. **Configure Cursor MCP** (see `cursor_mcp_config.json`)

4. **Test the fixes** using the test scripts

## Test Scenarios

These tests verify that Issue #8 is fixed:

- ✅ `dune_query` accepts `None` for parameters
- ✅ `dune_query` accepts dict for parameters  
- ✅ No "overloaded function" errors
- ✅ Raw SQL queries work correctly
- ✅ Discovery tools work without 404 errors

## Files

- `cursor_mcp_config.json` - Cursor MCP configuration
- `test_basic_query.py` - Basic query execution tests
- `test_issue_8_scenarios.py` - Specific Issue #8 test cases
- `.env.example` - Template for .env file

