# Installation Guide for Testing Issue #8 Fixes

## Important: Install from Source

**DO NOT** install from PyPI (`uv pip install spice-mcp==0.1.3`) - that version doesn't have the Issue #8 fixes yet.

You **MUST** install from the local source code to test the latest changes:

```bash
cd /Users/evandekim/Documents/spice_mcp
uv pip install -e .
```

The `-e` flag installs in "editable" mode, so changes to the source code are immediately available.

## Verify Installation

Check that you're using the local version:

```bash
uv pip list | grep spice-mcp
```

Should show:
```
spice-mcp    0.1.3    /Users/evandekim/Documents/spice_mcp
```

If it shows a different path or PyPI URL, the installation is wrong.

## Verify the Fixes Are Present

Check that the type annotations use `Optional`:

```bash
grep -A 5 "def dune_query" src/spice_mcp/mcp/server.py | grep parameters
```

Should show:
```python
parameters: Optional[dict[str, Any]] = None,
```

If it shows `dict[str, Any] | None`, the changes aren't applied.

## Testing with Cursor MCP

1. **Install from source** (see above)
2. **Set up .env** file with your DUNE_API_KEY
3. **Configure Cursor** (see CURSOR_SETUP.md)
4. **Run tests**: `python test_mcp_cursor/test_issue_8_scenarios.py`

## Troubleshooting

### "spice-mcp command not found"

Make sure you installed with `uv pip install -e .` and that your Python environment is in PATH.

### Still getting overloaded function errors

1. Verify you're using the local source: `uv pip list | grep spice-mcp`
2. Check the file has `Optional` annotations: `grep "Optional\[dict" src/spice_mcp/mcp/server.py`
3. Restart Cursor completely after installation
4. Check Cursor's MCP logs for detailed error messages

### Changes not taking effect

1. Reinstall: `uv pip uninstall spice-mcp && uv pip install -e .`
2. Restart Cursor
3. Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`

