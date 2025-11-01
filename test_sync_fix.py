#!/usr/bin/env python3
"""
Test the synchronous fix for raw SQL execution.
"""

import os
import sys
sys.path.insert(0, '/Users/evandekim/Documents/spice_mcp/src')

from spice_mcp.mcp.server import dune_query

def test_sync_dune_query():
    """Test the sync version of dune_query tool"""
    print("🐛 Testing synchronous dune_query tool...")
    
    # Set up environment if needed
    if not os.getenv('DUNE_API_KEY'):
        print("❌ DUNE_API_KEY not set")
        return False
    
    try:
        result = dune_query(
            query="SELECT 1 as test",
            refresh=True,
            format="preview"
        )
        
        print(f"✅ Result type: {type(result)}")
        print(f"✅ Result keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}")
        
        if isinstance(result, dict):
            print(f"✅ Response type: {result.get('type')}")
            print(f"✅ Row count: {result.get('rowcount')}")
            print(f"✅ Execution ID: {result.get('execution_id')}")
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                return False
            else:
                print("✅ Success! Synchronous dune_query executed raw SQL correctly")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_sync_dune_query()
    if success:
        print("\n✅ Synchronous fix working!")
    else:
        print("\n❌ Synchronous fix failed!")
    sys.exit(0 if success else 1)
