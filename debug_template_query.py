#!/usr/bin/env python3
"""
Debug script to test template query 4060379 execution directly.
"""

import os
import sys
import json

# Add src to path
sys.path.insert(0, '/Users/evandekim/Documents/spice_mcp/src')

from spice_mcp.adapters.dune import extract, urls

def test_template_query_directly():
    """Test the template query directly via extract.query()"""
    
    # Ensure API key is available
    api_key = os.getenv('DUNE_API_KEY')
    if not api_key:
        print("❌ DUNE_API_KEY not set")
        return False
    
    template_id = int(os.getenv("SPICE_RAW_SQL_QUERY_ID", "4060379"))
    print(f"🔍 Testing template query {template_id} directly...")
    
    try:
        # Test 1: Execute simple raw SQL
        print("\n📝 Test 1: Simple SELECT 1")
        result = extract.query(
            query_or_execution="SELECT 1 as test",
            verbose=True,
            refresh=True,
            poll=True,
            api_key=api_key,
            timeout_seconds=30
        )
        
        print(f"✅ Result type: {type(result)}")
        if hasattr(result, 'shape'):
            print(f"✅ Result shape: {result.shape}")
        print(f"✅ Result columns: {list(result.columns) if hasattr(result, 'columns') else 'N/A'}")
        
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        print(f"   Error type: {type(e)}")
        return False
    
    try:
        # Test 2: Test with parameters explicitly
        print("\n📝 Test 2: Raw SQL with explicit parameters")
        result = extract.query(
            query_or_execution="SELECT 1 as test",
            verbose=True,
            refresh=True,
            poll=True,
            api_key=api_key,
            parameters={'query': 'SELECT 1 as test'},
            timeout_seconds=30
        )
        
        print(f"✅ Result type: {type(result)}")
        if hasattr(result, 'shape'):
            print(f"✅ Result shape: {result.shape}")
            
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False
    
    return True

def test_determine_input_type():
    """Test the determine_input_type function"""
    print("\n🔍 Testing determine_input_type...")
    
    query_id, execution, parameters = extract.determine_input_type("SELECT 1 as test")
    
    print(f"✅ Query ID: {query_id}")
    print(f"✅ Execution: {execution}")
    print(f"✅ Parameters: {parameters}")
    
    return True

def test_template_query_api_check():
    """Check if the template query actually exists and is accessible"""
    template_id = int(os.getenv("SPICE_RAW_SQL_QUERY_ID", "4060379"))
    api_key = os.getenv('DUNE_API_KEY')
    
    if not api_key:
        print("❌ DUNE_API_KEY not set")
        return False
        
    print(f"\n🔍 Checking template query {template_id} metadata...")
    
    try:
        # Check if the query exists by trying to get its info
        url = urls.get_query_execute_url(template_id)
        headers = {'X-Dune-API-Key': api_key, 'User-Agent': extract.get_user_agent()}
        
        print(f"🌐 Query execute URL: {url}")
        
        # Try to execute with empty parameters first
        import requests
        
        response = requests.post(
            url, 
            headers=headers,
            json={'query_parameters': {}, 'performance': 'medium'},
            timeout=30
        )
        
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Execution result: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ API Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Template query check failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🐛 Debugging spice-mcp raw SQL execution issues...")
    
    success = True
    
    # Test 1: Determine input type
    success &= test_determine_input_type()
    
    # Test 2: Check template query API
    success &= test_template_query_api_check()
    
    # Test 3: Direct execution
    print(f"\n🚀 About to test raw SQL execution...")
    success &= test_template_query_directly()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
