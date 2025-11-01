#!/bin/bash
# Setup script for Cursor MCP configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Setting up Cursor MCP test environment..."
echo ""

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "📝 Please edit test_mcp_cursor/.env and add your DUNE_API_KEY"
    echo ""
fi

# Install spice-mcp from source
echo "📦 Installing spice-mcp from source..."
cd "$REPO_ROOT"
uv pip install -e . > /dev/null 2>&1 || {
    echo "❌ Failed to install spice-mcp. Make sure you're in the repo root."
    exit 1
}
echo "✅ spice-mcp installed"

# Verify installation
echo ""
echo "🔍 Verifying installation..."
if command -v spice-mcp &> /dev/null; then
    echo "✅ spice-mcp command found"
else
    echo "❌ spice-mcp command not found. Check your PATH."
    exit 1
fi

# Check for API key
if grep -q "your-api-key-here" "$SCRIPT_DIR/.env" 2>/dev/null; then
    echo "⚠️  Warning: DUNE_API_KEY not set in .env file"
    echo "   Edit test_mcp_cursor/.env and add your API key"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit test_mcp_cursor/.env and add your DUNE_API_KEY"
echo "2. Configure Cursor MCP (see cursor_mcp_config.json)"
echo "3. Run tests: python test_mcp_cursor/test_issue_8_scenarios.py"
echo ""
echo "Cursor MCP Configuration:"
echo "  Add this to Cursor Settings → MCP Servers:"
echo ""
cat "$SCRIPT_DIR/cursor_mcp_config.json" | sed 's/^/  /'
echo ""

