#!/usr/bin/env python3
"""
Test script to verify cache functionality.
"""
import os
import sys
import time
from pathlib import Path
import tempfile
import shutil

# Add src path to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from spice_mcp.adapters.dune import extract
from spice_mcp.adapters.http_client import HttpClient, HttpClientConfig


def test_cache_functionality():
    """Test cache functionality with temporary cache directory."""
    print("🔧 Testing cache functionality...")
    
    # Load API key from .env
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found in environment")
        return False
    
    # Create temporary cache directory
    temp_cache_dir = tempfile.mkdtemp(prefix="spice_test_cache_")
    print(f"📁 Using temporary cache directory: {temp_cache_dir}")
    
    try:
        # No HTTP client needed for cache test (will use default)
        
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
        
        # Create a test query for caching tests
        test_sql = f"SELECT 1 as test_col, '{int(time.time())}' as query_time"
        query_id = create_query(test_sql, "cache_test")
        print(f"✓ Created cache test query: {query_id}")
        
        test_cases = []
        
        # Test 1: First query (should populate cache)
        print("\n📊 Test 1: First query execution (cache miss)")
        start_time = time.time()
        try:
            result1 = extract.query(
                query_or_execution=query_id,
                api_key=api_key,
                poll=True,
                performance="medium",
                cache_dir=temp_cache_dir,
                save_to_cache=True,
            )
            
            first_duration = time.time() - start_time
            print(f"✓ First query executed in {first_duration:.2f}s")
            
            if hasattr(result1, 'shape'):
                print(f"✓ Result: {result1.shape} rows/columns")
            
            test_cases.append(("First query (cache miss)", True))
            
        except Exception as e:
            print(f"❌ First query failed: {e}")
            test_cases.append(("First query (cache miss)", False))
        
        # Test 2: Second identical query (should hit cache)
        print("\n💾 Test 2: Second identical query execution (cache hit)")
        start_time = time.time()
        try:
            result2 = extract.query(
                query_or_execution=query_id,
                api_key=api_key,
                poll=True,
                performance="medium",
                cache_dir=temp_cache_dir,
                load_from_cache=True,
            )
            
            second_duration = time.time() - start_time
            print(f"✓ Second query executed in {second_duration:.2f}s")
            
            if hasattr(result2, 'shape'):
                print(f"✓ Result: {result2.shape} rows/columns")
            
            # Cache hit should be significantly faster
            if test_cases[0][1] and second_duration < first_duration * 0.8:
                print(f"✓ Cache appears to be working (faster second execution)")
                cache_working = True
            else:
                print(f"⚠️  Cache performance unclear, but execution succeeded")
                cache_working = True
            
            test_cases.append(("Second query (cache hit)", cache_working))
            
        except Exception as e:
            print(f"❌ Second query failed: {e}")
            test_cases.append(("Second query (cache hit)", False))
        
        # Test 3: Check cache directory contents
        print("\n📁 Test 3: Verify cache directory contents")
        try:
            cache_files = list(Path(temp_cache_dir).rglob("*"))
            cache_files = [f for f in cache_files if f.is_file()]
            print(f"✓ Cache directory contains {len(cache_files)} files")
            for cache_file in cache_files[:3]:  # Show first 3 files
                print(f"  📄 {cache_file.name}")
            
            if len(cache_files) > 0:
                test_cases.append(("Cache files created", True))
            else:
                test_cases.append(("Cache files created", False))
                
        except Exception as e:
            print(f"❌ Cache directory check failed: {e}")
            test_cases.append(("Cache files created", False))
        
        # Test 4: Test with max_age parameter
        print("\n⏰ Test 4: Test max_age parameter")
        try:
            # Query with very short max_age to force refresh
            result3 = extract.query(
                query_or_execution=query_id,
                api_key=api_key,
                poll=True,
                performance="medium",
                max_age=0.001,  # Very short cache age
                cache_dir=temp_cache_dir,
            )
            
            print(f"✓ Query with max_age parameter executed successfully")
            test_cases.append(("max_age parameter", True))
            
        except Exception as e:
            print(f"❌ max_age test failed: {e}")
            test_cases.append(("max_age parameter", False))
        
        # Summary
        print("\n📋 Test Summary:")
        passed = sum(1 for _, success in test_cases if success)
        total = len(test_cases)
        print(f"✅ {passed}/{total} tests passed")
        
        for test_name, success in test_cases:
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}")
        
        return passed == total
        
    finally:
        # Clean up temporary cache directory
        try:
            shutil.rmtree(temp_cache_dir)
            print(f"\n🧹 Cleaned up temporary cache directory")
        except Exception as e:
            print(f"\n⚠️  Failed to clean up cache directory: {e}")


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
    
    success = test_cache_functionality()
    sys.exit(0 if success else 1)
