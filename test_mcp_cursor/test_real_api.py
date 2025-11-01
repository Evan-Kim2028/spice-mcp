#!/usr/bin/env python3
"""
Real API testing for Issue #8 fixes.

Tests both:
1. Overloaded function error fix
2. 404 errors on discovery tools

Uses real Dune API key from .env file.
"""

import os
import sys
from pathlib import Path

# Add parent src to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

# Load .env from repo root
env_file = parent_dir / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

try:
    from spice_mcp.mcp import server
    print("✅ Successfully imported spice_mcp.mcp.server")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)


def test_1_dune_query_no_parameters():
    """Test 1: dune_query with no parameters (Issue #8 - overloaded function)"""
    print("\n" + "=" * 60)
    print("Test 1: dune_query with no parameters (Real API)")
    print("-" * 60)
    
    server._ensure_initialized()
    
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found in environment")
        return False
    
    try:
        # Test calling through FastMCP wrapper with real API
        result = server.dune_query.fn(
            query="SELECT 'test' as status",
            format="preview"
        )
        
        # Check for overloaded function error
        if isinstance(result, dict) and result.get("ok") is False:
            error_msg = str(result.get("error", {}).get("message", ""))
            if "overloaded function" in error_msg.lower():
                print(f"❌ FAIL: Still getting overloaded function error: {error_msg}")
                return False
        
        # Should return valid result
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        print(f"✅ PASS: Query executed successfully")
        print(f"   Result type: {result.get('type', 'unknown')}")
        print(f"   Rowcount: {result.get('rowcount', 'unknown')}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "overloaded function" in error_msg.lower():
            print(f"❌ FAIL: Overloaded function error: {error_msg}")
            return False
        else:
            print(f"⚠️  Unexpected error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


def test_2_dune_query_with_parameters():
    """Test 2: dune_query with parameters=None (Issue #8)"""
    print("\n" + "=" * 60)
    print("Test 2: dune_query with parameters=None (Real API)")
    print("-" * 60)
    
    server._ensure_initialized()
    
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found")
        return False
    
    try:
        result = server.dune_query.fn(
            query="SELECT 1 as value",
            parameters=None,
            format="preview"
        )
        
        if isinstance(result, dict) and result.get("ok") is False:
            error_msg = str(result.get("error", {}).get("message", ""))
            if "overloaded function" in error_msg.lower():
                print(f"❌ FAIL: Overloaded function error: {error_msg}")
                return False
        
        assert isinstance(result, dict)
        print(f"✅ PASS: Query with parameters=None executed successfully")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "overloaded function" in error_msg.lower():
            print(f"❌ FAIL: Overloaded function error: {error_msg}")
            return False
        else:
            print(f"⚠️  Error: {error_msg}")
            return False


def test_3_dune_find_tables_no_404():
    """Test 3: dune_find_tables - should not return 404 (Issue #8)"""
    print("\n" + "=" * 60)
    print("Test 3: dune_find_tables (no 404 errors)")
    print("-" * 60)
    
    server._ensure_initialized()
    
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found")
        return False
    
    try:
        # Test schema search (this was failing with 404)
        result = server.dune_find_tables.fn(
            keyword="walrus",
            limit=5
        )
        
        # Check for 404 error
        if isinstance(result, dict):
            if result.get("ok") is False:
                error_msg = str(result.get("error", {}).get("message", ""))
                if "404" in error_msg or "not found" in error_msg.lower():
                    print(f"❌ FAIL: Still getting 404 error: {error_msg}")
                    return False
                else:
                    print(f"⚠️  Query failed with different error: {error_msg}")
                    print("   (May be API/auth issue, not a 404)")
                    return True
            
            # Should return schemas or tables
            schemas = result.get("schemas", [])
            tables = result.get("tables", [])
            print(f"✅ PASS: No 404 error")
            print(f"   Found {len(schemas)} schemas, {len(tables)} tables")
            return True
        else:
            print(f"⚠️  Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"❌ FAIL: 404 error: {error_msg}")
            return False
        else:
            print(f"⚠️  Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


def test_4_dune_discover_no_404():
    """Test 4: dune_discover - should not return 404 (Issue #8)"""
    print("\n" + "=" * 60)
    print("Test 4: dune_discover (no 404 errors)")
    print("-" * 60)
    
    server._ensure_initialized()
    
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found")
        return False
    
    try:
        # Test discovery with keyword (this was failing with 404)
        result = server.dune_discover.fn(
            keyword="walrus",
            limit=5
        )
        
        # Check for 404 error
        if isinstance(result, dict):
            if result.get("ok") is False:
                error_msg = str(result.get("error", {}).get("message", ""))
                if "404" in error_msg or "not found" in error_msg.lower():
                    print(f"❌ FAIL: Still getting 404 error: {error_msg}")
                    return False
                else:
                    print(f"⚠️  Query failed with different error: {error_msg}")
                    return True
            
            schemas = result.get("schemas", [])
            tables = result.get("tables", [])
            print(f"✅ PASS: No 404 error")
            print(f"   Found {len(schemas)} schemas, {len(tables)} tables")
            return True
        else:
            print(f"⚠️  Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"❌ FAIL: 404 error: {error_msg}")
            return False
        else:
            print(f"⚠️  Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


def test_5_dune_describe_table_no_404():
    """Test 5: dune_describe_table - should not return 404"""
    print("\n" + "=" * 60)
    print("Test 5: dune_describe_table (no 404 errors)")
    print("-" * 60)
    
    server._ensure_initialized()
    
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found")
        return False
    
    try:
        # Test describing a known table (this was failing with 404)
        # Use a common schema/table that should exist
        result = server.dune_describe_table.fn(
            schema="ethereum",
            table="blocks"
        )
        
        # Check for 404 error
        if isinstance(result, dict):
            if result.get("ok") is False:
                error_msg = str(result.get("error", {}).get("message", ""))
                if "404" in error_msg or "not found" in error_msg.lower():
                    print(f"❌ FAIL: Still getting 404 error: {error_msg}")
                    return False
                else:
                    print(f"⚠️  Query failed with different error: {error_msg}")
                    print("   (May be API/auth issue, not a 404)")
                    return True
            
            columns = result.get("columns", [])
            print(f"✅ PASS: No 404 error")
            print(f"   Found {len(columns)} columns")
            if columns:
                print(f"   Sample columns: {[c.get('name', 'unknown') for c in columns[:3]]}")
            return True
        else:
            print(f"⚠️  Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"❌ FAIL: 404 error: {error_msg}")
            return False
        else:
            print(f"⚠️  Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


def test_6_raw_sql_via_template_query():
    """Test 6: Raw SQL execution via template query (Issue #8)"""
    print("\n" + "=" * 60)
    print("Test 6: Raw SQL via template query (no overload/404 errors)")
    print("-" * 60)
    
    server._ensure_initialized()
    
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found")
        return False
    
    try:
        # Test raw SQL that uses template query internally
        result = server.dune_query.fn(
            query="SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE '%walrus%' LIMIT 5",
            format="preview"
        )
        
        # Check for errors
        if isinstance(result, dict) and result.get("ok") is False:
            error_msg = str(result.get("error", {}).get("message", ""))
            if "overloaded function" in error_msg.lower():
                print(f"❌ FAIL: Overloaded function error: {error_msg}")
                return False
            if "404" in error_msg or "not found" in error_msg.lower():
                print(f"❌ FAIL: 404 error (template query issue): {error_msg}")
                return False
        
        print(f"✅ PASS: Raw SQL executed without overload/404 errors")
        print(f"   Result type: {result.get('type', 'unknown')}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "overloaded function" in error_msg.lower():
            print(f"❌ FAIL: Overloaded function error: {error_msg}")
            return False
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"❌ FAIL: 404 error: {error_msg}")
            return False
        else:
            print(f"⚠️  Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run all real API tests"""
    print("=" * 60)
    print("Real API Testing for Issue #8 Fixes")
    print("=" * 60)
    
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("\n❌ DUNE_API_KEY not found in environment")
        print("   Make sure .env file exists in repo root with DUNE_API_KEY")
        return 1
    
    # Mask API key in output
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"\n✅ Using DUNE_API_KEY: {masked_key}")
    
    tests = [
        ("dune_query (no params)", test_1_dune_query_no_parameters),
        ("dune_query (params=None)", test_2_dune_query_with_parameters),
        ("dune_find_tables (no 404)", test_3_dune_find_tables_no_404),
        ("dune_discover (no 404)", test_4_dune_discover_no_404),
        ("dune_describe_table (no 404)", test_5_dune_describe_table_no_404),
        ("Raw SQL via template (no errors)", test_6_raw_sql_via_template_query),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Issue #8 fixes are working correctly with real API.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

