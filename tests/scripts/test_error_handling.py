#!/usr/bin/env python3
"""
Test script to verify error handling functionality.
"""
import os
import sys
from pathlib import Path

# Add src path to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from spice_mcp.adapters.dune import extract
from spice_mcp.adapters.http_client import HttpClient, HttpClientConfig


def test_error_handling():
    """Test error handling for various failure scenarios."""
    print("🔧 Testing error handling...")
    
    # No HTTP client needed for error test
    
    test_cases = []
    
    # Test 1: Invalid API key
    print("\n❌ Test 1: Invalid API key")
    try:
        result = extract.query(
            query_or_execution="SELECT 1",
            api_key="invalid",  # intentionally invalid for test
            poll=True,
            performance="medium",
            
        )
        
        print("❌ Expected authentication error but got success")
        test_cases.append(("Invalid API key", False))
        
    except Exception as e:
        print(f"✓ Correctly caught authentication error: {type(e).__name__}: {str(e)[:100]}...")
        test_cases.append(("Invalid API key", True))
    
    # Test 2: Invalid query ID
    print("\n❌ Test 2: Invalid query ID")
    try:
        # Use a very large, non-existent query ID
        result = extract.query(
            query_or_execution=999999999,
            api_key=os.getenv("DUNE_API_KEY", "dummy"),
            poll=True,
            performance="medium",
            
        )
        
        print("❌ Expected query not found error but got success")
        test_cases.append(("Invalid query ID", False))
        
    except Exception as e:
        print(f"✓ Correctly caught query error: {type(e).__name__}: {str(e)[:100]}...")
        test_cases.append(("Invalid query ID", True))
    
    # Test 3: Invalid SQL syntax
    print("\n❌ Test 3: Invalid SQL syntax")
    api_key = os.getenv("DUNE_API_KEY")
    if api_key:
        try:
            result = extract.query(
                query_or_execution="SELECTTTT INVALID SQL SYNTAX",
                api_key=api_key,
                poll=True,
                performance="medium",
                
            )
            
            print("❌ Expected SQL syntax error but got success")
            test_cases.append(("Invalid SQL syntax", False))
            
        except Exception as e:
            print(f"✓ Correctly caught SQL error: {type(e).__name__}: {str(e)[:100]}...")
            test_cases.append(("Invalid SQL syntax", True))
    else:
        print("⚠️  Skipping SQL test - no API key available")
        test_cases.append(("Invalid SQL syntax", None))
    
    # Test 4: Empty query
    print("\n❌ Test 4: Empty query")
    try:
        result = extract.query(
            query_or_execution="",
            api_key=api_key,
            poll=True,
            performance="medium",
            
        )
        
        print("❌ Expected empty query error but got success")
        test_cases.append(("Empty query", False))
        
    except Exception as e:
        print(f"✓ Correctly caught empty query error: {type(e).__name__}: {str(e)[:100]}...")
        test_cases.append(("Empty query", True))
    
    # Test 5: Missing required parameters in parameterized query
    print("\n❌ Test 5: Missing required parameters")
    if api_key:
        try:
            result = extract.query(
                query_or_execution="SELECT {{missing_param}} as value",
                api_key=api_key,
                poll=True,
                performance="medium",
                
            )
            
            print("❌ Expected missing parameter error but got success")
            test_cases.append(("Missing parameters", False))
            
        except Exception as e:
            print(f"✓ Correctly caught parameter error: {type(e).__name__}: {str(e)[:100]}...")
            test_cases.append(("Missing parameters", True))
    else:
        print("⚠️  Skipping parameter test - no API key available")
        test_cases.append(("Missing parameters", None))
    
    # Test 6: Timeout handling (with very short timeout)
    print("\n⏰ Test 6: Timeout handling")
    if api_key:
        try:
            # Use a complex query with very short timeout
            complex_query = """
            SELECT 
                block_number,
                block_time
            FROM ethereum.blocks 
            WHERE block_time > NOW() - INTERVAL '1 hour'
            ORDER BY block_number DESC
            LIMIT 1000
            """
            
            result = extract.query(
                query_or_execution=complex_query,
                api_key=api_key,
                poll=True,
                performance="large",
                timeout_seconds=0.001,  # Very short timeout
                
            )
            
            print("⚠️  Query completed before timeout (could be normal)")
            test_cases.append(("Timeout handling", None))
            
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                print(f"✓ Correctly caught timeout error: {type(e).__name__}: {str(e)[:100]}...")
                test_cases.append(("Timeout handling", True))
            else:
                print(f"⚠️  Caught different error: {type(e).__name__}: {str(e)[:100]}...")
                test_cases.append(("Timeout handling", None))
    else:
        print("⚠️  Skipping timeout test - no API key available")
        test_cases.append(("Timeout handling", None))
    
    # Summary
    print("\n📋 Test Summary:")
    passed = sum(1 for _, success in test_cases if success is True)
    skipped = sum(1 for _, success in test_cases if success is None)
    failed = sum(1 for _, success in test_cases if success is False)
    total = len(test_cases)
    
    print(f"✅ {passed} tests passed")
    print(f"⚠️  {skipped} tests skipped")
    print(f"❌ {failed} tests failed")
    print(f"📊 Total: {total} tests")
    
    for test_name, success in test_cases:
        if success is True:
            status = "✅"
        elif success is None:
            status = "⚠️"
        else:
            status = "❌"
        print(f"  {status} {test_name}")
    
    # Consider the test successful if we passed most tests and didn't have explicit failures
    return failed == 0


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
    
    success = test_error_handling()
    sys.exit(0 if success else 1)
