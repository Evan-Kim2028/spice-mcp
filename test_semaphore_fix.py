#!/usr/bin/env python3
"""
Test script to verify the semaphore fix works for raw SQL execution.
"""

import os
import sys
import asyncio
sys.path.insert(0, '/Users/evandekim/Documents/spice_mcp/src')

from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
from spice_mcp.config import Config, DuneConfig, CacheConfig, HttpClientConfig
from spice_mcp.logging.query_history import QueryHistory
from spice_mcp.service_layer.query_service import QueryService
from spice_mcp.adapters.dune.client import DuneAdapter
from pathlib import Path

def test_direct_vs_mcp_calls():
    """Test the difference between direct tool calls and MCP server calls."""
    
    # Ensure API key is available
    api_key = os.getenv('DUNE_API_KEY')
    if not api_key:
        print("❌ DUNE_API_KEY not set")
        return False
    
    print("🔍 Comparing direct tool calls vs MCP server calls...")
    
    # Setup all components
    config = Config(
        dune=DuneConfig(api_key=api_key),
        cache=CacheConfig(),
        http=HttpClientConfig()
    )
    
    adapter = DuneAdapter(config)
    query_service = QueryService(adapter)
    query_history = QueryHistory(Path("/tmp/query_history.jsonl"), Path("/tmp/sql_artifacts"))
    
    # Create the tool
    tool = ExecuteQueryTool(config, query_service, query_history)
    
    try:
        # Test 1: Direct tool call (this should work)
        print("\n📝 Test 1: Direct tool call")
        direct_result = asyncio.run(tool.execute(
            query="SELECT 1 as test",
            refresh=True,
            format="preview"
        ))
        print(f"✅ Direct call succeeded: {type(direct_result)}, keys: {list(direct_result.keys()) if isinstance(direct_result, dict) else 'not dict'}")
        
        # Test 2: MCP server call (simulate what fails)
        print("\n📝 Test 2: MCP server call simulation")
        
        # Import the server module
        from spice_mcp.mcp import server as mcp_server
        
        # Initialize the server
        mcp_server._ensure_initialized()
        mcp_server.EXECUTE_QUERY_TOOL = tool  # Use our tool instance
        
        # Try calling the MCP tool function
        mcp_result = asyncio.run(mcp_server.dune_query(
            query="SELECT 1 as test",
            refresh=True,
            format="preview"
        ))
        print(f"✅ MCP call succeeded: {type(mcp_result)}, keys: {list(mcp_result.keys()) if isinstance(mcp_result, dict) else 'not dict'}")
        
        # Compare results
        print("\n📊 Comparison:")
        print(f"Direct call execution_id: {direct_result.get('execution_id', 'N/A')}")
        print(f"MCP call execution_id: {mcp_result.get('execution_id', 'N/A')}")
        
        # Check if both have execution_ids
        if (direct_result.get('execution_id') and direct_result.get('execution_id') != 'unknown' and
            mcp_result.get('execution_id') and mcp_result.get('execution_id') != 'unknown'):
            print("✅ SUCCESS: Both calls have valid execution IDs!")
            return True
        else:
            print("❌ FAILURE: One or both calls failed to get execution ID")
            if (mcp_result.get('execution_id') == 'unknown'):
                print("   MCP call has execution_id='unknown' - this is the bug!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🐛 Testing semaphore removal fix...")
    success = test_direct_vs_mcp_calls()
    
    if success:
        print("\n✅ Semaphore removal fix works!")
    else:
        print("\n❌ Semaphore removal fix still issues!")
    sys.exit(0 if success else 1)
