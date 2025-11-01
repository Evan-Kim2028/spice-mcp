#!/usr/bin/env python3
"""
Debug script to figure out what's happening with the Dune API calls.
"""
import os
import sys
from pathlib import Path

# Add src to path  
src_path = Path('src')
sys.path.insert(0, str(src_path))

from spice_mcp.adapters.dune import urls, transport

def test_dune_connection():
    """Test API connectivity directly."""
    print("🔧 Debugging Dune API connection...")
    
    api_key = os.getenv("DUNE_API_KEY")
    print(f"API key: {api_key[:8] if api_key else 'None'}...")
    
    try:
        # Test1: Check headers
        headers = urls.get_headers(api_key=api_key)
        print(f"Headers: {headers}")
        
        # Test2: Simple URL construction
        url = urls.get_query_execute_url("SELECT 1 as test")
        print(f"URL for raw SQL: {url}")
        
        # Test3: Try a direct API call
        print("\n📡 Testing direct API call...")
        test_url = urls.url_templates['query_create']
        print(f"Test URL: {test_url}")
        
        response = transport.post(
            test_url,
            headers=headers,
            json={
                "query_sql": "SELECT 1 as test_col",
                "name": "debug_test",
                "dataset": "preview",
                "is_private": True
            },
            timeout=10.0
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            query_id = data.get('query_id')
            print(f"✓ Created query with ID: {query_id}")
            
            # Now try to execute it
            execute_url = urls.get_query_execute_url(query_id)
            execute_response = transport.post(
                execute_url,
                headers=headers,
                json={
                    "performance": "medium",
                    "query_parameters": {}
                },
                timeout=10.0
            )
            
            print(f"Execute response status: {execute_response.status_code}")
            print(f"Execute response: {execute_response.text[:200]}...")
            
            if execute_response.status_code == 200:
                exec_data = execute_response.json()
                execution_id = exec_data.get('execution_id')
                print(f"✓ Created execution with ID: {execution_id}")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Load env
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
    
    success = test_dune_connection()
    sys.exit(0 if success else 1)
