#!/usr/bin/env python3
"""
Debug script to test the MCP tool layer directly.
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, '/Users/evandekim/Documents/spice_mcp/src')

from spice_mcp.config import Config
from spice_mcp.logging.query_history import QueryHistory
from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
from spice_mcp.service_layer.query_service import QueryService
from spice_mcp.adapters.dune.client import DuneAdapter

def test_mcp_tool_directly():
    """Test the MCP tool directly"""
    
    # Ensure API key is available
    api_key = os.getenv('DUNE_API_KEY')
    if not api_key:
        print("❌ DUNE_API_KEY not set")
        return False
    
    print("🔍 Testing MCP tool directly...")
    
    try:
        # Setup the components
        from spice_mcp.config import DuneConfig, CacheConfig, HttpClientConfig
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
        
        # Test simple raw SQL
        print("\n📝 Testing MCP tool with 'SELECT 1 as test'")
        
        # This should work via the MCP tool interface
        import asyncio
        result = asyncio.run(tool.execute(
            query="SELECT 1 as test",
            refresh=True,
            format="preview"
        ))
        
        print(f"✅ Tool result type: {type(result)}")
        print(f"✅ Tool result keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}")
        
        if isinstance(result, dict):
            print(f"✅ Response type: {result.get('type')}")
            print(f"✅ Row count: {result.get('rowcount')}")
            print(f"✅ Execution ID: {result.get('execution_id')}")
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                return False
            else:
                print("✅ Success! MCP tool executed raw SQL correctly")
        
    except Exception as e:
        print(f"❌ MCP tool test failed: {e}")
        print(f"   Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_service_layer_directly():
    """Test the service layer directly"""
    
    # Ensure API key is available
    api_key = os.getenv('DUNE_API_KEY')
    if not api_key:
        print("❌ DUNE_API_KEY not set")
        return False
    
    print("🔍 Testing service layer directly...")
    
    try:
        # Setup the components
        from spice_mcp.config import DuneConfig, CacheConfig, HttpClientConfig
        config = Config(
            dune=DuneConfig(api_key=api_key),
            cache=CacheConfig(),
            http=HttpClientConfig()
        )
        adapter = DuneAdapter(config)
        query_service = QueryService(adapter)
        
        # Test service layer directly
        print("\n📝 Testing service layer with 'SELECT 1 as test'")
        
        result = query_service.execute(
            query="SELECT 1 as test",
            refresh=True,
            include_execution=True
        )
        
        print(f"✅ Service result type: {type(result)}")
        print(f"✅ Service result keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}")
        
        if isinstance(result, dict):
            print(f"✅ Row count: {result.get('rowcount')}")
            print(f"✅ Execution: {result.get('execution')}")
            if 'execution' in result and result['execution'].get('execution_id'):
                print("✅ Service layer executed successfully!")
                return True
            else:
                print("❌ Service layer failed - no execution ID")
                return False
        
    except Exception as e:
        print(f"❌ Service layer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return False

if __name__ == "__main__":
    print("🐛 Debugging spice-mcp MCP tool layer...")
    
    success = True
    
    # Test 1: Service layer
    success &= test_service_layer_directly()
    
    # Test 2: MCP tool
    success &= test_mcp_tool_directly()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
