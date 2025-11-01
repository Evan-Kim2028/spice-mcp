#!/usr/bin/env python3
"""
Test script to verify Dune API connectivity and authentication.
"""
import os
import sys
from pathlib import Path

# Add src path to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from spice_mcp.adapters.dune import extract


def test_dune_connectivity():
    """Test basic Dune API connectivity with API key from .env."""
    print("🔧 Testing Dune API connectivity...")
    
    # Load API key from .env
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found in environment")
        return False
    
    print(f"✓ API key found: {api_key[:8]}...")
    
    try:
        # Test basic connectivity by running a simple query with known working query ID
        print("📡 Testing API authentication...")
        
        # First create a simple query and get its ID
        from spice_mcp.adapters.dune import urls
        
        headers = urls.get_headers(api_key=api_key)
        create_url = urls.url_templates['query_create']
        
        import requests as req
        create_response = req.post(
            create_url,
            headers=headers,
            json={
                "query_sql": "SELECT 1 as test_col, 'connectivity_test' as message",
                "name": "connectivity_test",
                "dataset": "preview",
                "is_private": True
            },
            timeout=10.0
        )
        
        if create_response.status_code != 200:
            print(f"❌ Failed to create test query: {create_response.status_code}")
            return False
            
        query_id = create_response.json()['query_id']
        print(f"✓ Created test query: {query_id}")
        
        # Now test the query execution using the created query ID
        result = extract.query(
            query_or_execution=query_id,
            api_key=api_key,
            poll=True,  # Wait for completion
            performance="medium",
            limit=1,  # Only need 1 row to test connectivity
        )
        
        if hasattr(result, 'shape') and result.shape[0] > 0:
            print(f"✓ Authentication successful - got {result.shape[0]} row(s)")
            print(f"✓ Columns: {list(result.columns)}")
            print(f"✓ Sample data: {result.head(1).to_dict()}")
            return True
        else:
            print("❌ Query succeeded but no data returned")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == "__main__":
    # Set environment variables
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
    
    success = test_dune_connectivity()
    sys.exit(0 if success else 1)
