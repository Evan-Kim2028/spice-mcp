#!/usr/bin/env python3
"""
Test script to verify Dune query execution functionality.
"""
import os
import sys
from pathlib import Path

# Add src path to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from spice_mcp.adapters.dune import extract
from spice_mcp.adapters.http_client import HttpClient, HttpClientConfig


def test_query_execution():
    """Test various types of query execution."""
    print("🔧 Testing Dune query execution...")
    
    # Load API key from .env
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found in environment")
        return False
    
    test_cases = []
    
    # Helper function to create a query
    def create_query(sql, name):
        from spice_mcp.adapters.dune import urls
        headers = urls.get_headers(api_key=api_key)
        create_url = urls.url_templates['query_create']
        
        import requests as req
        response = req.post(
            create_url,
            headers=headers,
            json={
                "query_sql": sql,
                "name": name,
                "dataset": "preview",
                "is_private": True
            },
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to create query: {response.status_code} - {response.text}")
        
        return response.json()['query_id']
    
    # Test 1: Simple query via ID
    print("\n📝 Test 1: Execute simple query via ID")
    try:
        simple_sql = "SELECT 1 as test_col, 'hello' as message"
        query_id = create_query(simple_sql, "test_simple")
        print(f"✓ Created query ID: {query_id}")
        
        result = extract.query(
            query_or_execution=query_id,
            api_key=api_key,
            poll=True,
            performance="medium",
            limit=5,
        )
        
        if hasattr(result, 'shape'):
            rows, cols = result.shape
            print(f"✓ Simple query executed successfully: {rows} rows, {cols} columns")
            print(f"✓ Result: {result.to_dict()}")
        else:
            print(f"✓ Simple query executed successfully, result type: {type(result)}")
        
        test_cases.append(("Simple query", True))
        
    except Exception as e:
        print(f"❌ Simple query execution failed: {e}")
        test_cases.append(("Simple query", False))
    
    # Test 2: Query with parameters (using parameter syntax in SQL)
    print("\n🔧 Test 2: Execute query with parameters")
    try:
        param_sql = "SELECT {{test_param}} as value, 42 as number"
        query_id = create_query(param_sql, "test_params")
        print(f"✓ Created parameterized query ID: {query_id}")
        
        result = extract.query(
            query_or_execution=query_id,
            parameters={"test_param": "test_value"},
            api_key=api_key,
            poll=True,
            performance="medium",
            limit=5,
        )
        
        if hasattr(result, 'shape'):
            rows, cols = result.shape
            print(f"✓ Parameterized query executed successfully: {rows} rows, {cols} columns")
            print(f"✓ Result: {result.to_dict()}")
        else:
            print(f"✓ Parameterized query executed successfully, result type: {type(result)}")
        
        test_cases.append(("Parameterized query", True))
        
    except Exception as e:
        print(f"❌ Parameterized query execution failed: {e}")
        test_cases.append(("Parameterized query", False))
    
    # Test 3: More complex SQL query
    print("\n📊 Test 3: Execute complex SQL query")
    try:
        complex_sql = """
        SELECT 
            1 as id, 
            'test' as name, 
            CAST(123.45 AS DOUBLE) as value,
            DATE '2023-01-01' as test_date
        """
        query_id = create_query(complex_sql, "test_complex")
        print(f"✓ Created complex query ID: {query_id}")
        
        result = extract.query(
            query_or_execution=query_id,
            api_key=api_key,
            poll=True,
            performance="medium",
            limit=3,
        )
        
        if hasattr(result, 'shape'):
            rows, cols = result.shape
            print(f"✓ Complex query executed successfully: {rows} rows, {cols} columns")
            print(f"✓ Columns: {list(result.columns)}")
            print(f"✓ Sample: {result.head(1).to_dict()}")
        else:
            print(f"✓ Complex query executed successfully, result type: {type(result)}")
        
        test_cases.append(("Complex query", True))
        
    except Exception as e:
        print(f"❌ Complex query execution failed: {e}")
        test_cases.append(("Complex query", False))
    
    # Summary
    print("\n📋 Test Summary:")
    passed = sum(1 for _, success in test_cases if success)
    total = len(test_cases)
    print(f"✅ {passed}/{total} tests passed")
    
    for test_name, success in test_cases:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
    
    return passed == total


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
    
    success = test_query_execution()
    sys.exit(0 if success else 1)
