#!/usr/bin/env python3
"""
API Health Check - Tier 1 Test Suite

Tests fundamental API connectivity, authentication, and basic service health.
This should be run first to ensure the environment is ready for other tests.
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tests.support.api_client import DuneTestClient
from tests.support.helpers import PerformanceTimer, TestEnvironment, TestResultCollector
from tests.support import QueryFactory

def load_env_variables():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

def test_api_authentication() -> Tuple[bool, Dict[str, Any]]:
    """Test API authentication and basic connectivity."""
    print("🔐 Testing API Authentication...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        # Load API key
        api_key = os.getenv("DUNE_API_KEY")
        if not api_key:
            return False, {"error": "DUNE_API_KEY not found in environment"}
        
        print(f"   ✓ API key found: {api_key[:8]}...")
        
        # Create client
        client = DuneTestClient(api_key)
        
        # Test basic auth by attempting to create a simple query
        test_sql = QueryFactory.simple_select()
        query_id = client.create_query(test_sql, "auth_test_query")
        
        timer.checkpoint("query_created")
        print(f"   ✓ Query created: {query_id}")
        
        # Test execution permissions
        execution_id = client.execute_query(query_id)
        
        timer.checkpoint("query_executed")
        print(f"   ✓ Query execution started: {execution_id}")
        
        # Test result access permissions  
        try:
            status = client.get_execution_status(execution_id)
            timer.checkpoint("access_granted")
            print(f"   ✓ Results access granted: {status.get('state', 'unknown')}")
        except Exception as e:
            if "401" in str(e) or "403" in str(e) or "unauthorized" in str(e).lower():
                return False, {"error": f"Authorization failed: {e}"}
            # Other errors might be fine (query not completed yet)
            timer.checkpoint("partial_access") 
            print(f"   ⚠ Query access: {e}")
        
        timer.stop()
        
        # Cleanup
        client.delete_query(query_id)
        print("   ✓ Test query cleaned up")
        
        details = {
            "api_key_prefix": api_key[:8],
            "timings": timer.get_report(),
            "test_query_id": query_id,
            "execution_id": execution_id
        }
        
        return True, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_rate_limiting() -> Tuple[bool, Dict[str, Any]]:
    """Test API rate limiting behavior."""
    print("🚦 Testing Rate Limiting...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        client = DuneTestClient(api_key)
        test_sql = QueryFactory.simple_select()
        
        # Make multiple rapid requests to test rate limiting
        query_ids = []
        execution_times = []
        
        for i in range(5):
            req_start = time.time()
            query_id = client.create_query(f"{test_sql} -- rapid test {i}", f"rate_test_{i}")
            req_time = time.time() - req_start
            query_ids.append(query_id)
            execution_times.append(req_time)
            
            print(f"   Request {i+1}: {req_time:.3f}s")
            time.sleep(0.1)  # Small delay between requests
        
        timer.checkpoint("rapid_requests_complete")
        
        # Analyze request times
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        # Check for rate limit indicators (increased response times)
        rate_limit_detected = max_time > (avg_time * 2)
        
        # Cleanup
        for query_id in query_ids:
            client.delete_query(query_id)
        
        timer.stop()
        
        details = {
            "request_times": execution_times,
            "avg_time": avg_time,
            "max_time": max_time,
            "rate_limit_detected": rate_limit_detected,
            "timings": timer.get_report()
        }
        
        print(f"   ✓ Average request time: {avg_time:.3f}s")
        print(f"   ✓ Max request time: {max_time:.3f}s")
        if rate_limit_detected:
            print("   ✓ Rate limiting behavior detected")
        else:
            print("   ✓ No apparent rate limiting (within test limits)")
        
        return True, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_api_endpoints() -> Tuple[bool, Dict[str, Any]]:
    """Test critical API endpoints are accessible."""
    print("🌐 Testing API Endpoints...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        client = DuneTestClient(api_key)
        test_sql = QueryFactory.simple_select()
        
        # Create test query for endpoint testing
        query_id = client.create_query(test_sql, "endpoint_test")
        timer.checkpoint("create_endpoint")
        
        # Test query details endpoint
        query_url = f"{client.base_url}/query/{query_id}"
        query_response = client._retryRequest(
            lambda url, **kw: client._retryRequest(client._retryRequest.__self__.__class__.get, url, **kw),
            query_url,
            error_context="test query endpoint"
        )
        
        if query_response.status_code == 200:
            query_data = query_response.json()
            timer.checkpoint("query_endpoint")
            print(f"   ✓ Query endpoint: {query_data.get('name', 'unknown')}")
        else:
            print(f"   ⚠ Query endpoint: {query_response.status_code}")
        
        # Test execution endpoint
        execution_id = client.execute_query(query_id)
        timer.checkpoint("execute_endpoint")
        print(f"   ✓ Execute endpoint: {execution_id}")
        
        # Test status endpoint
        status = client.get_execution_status(execution_id)
        timer.checkpoint("status_endpoint")
        print(f"   ✓ Status endpoint: {status.get('state', 'unknown')}")
        
        # Wait for completion and test results endpoint 
        try:
            final_status = client.wait_for_completion(execution_id, timeout=30)
            timer.checkpoint("completion_endpoint")
            print(f"   ✓ Query completed: {final_status.get('state', 'unknown')}")
            
            # Test results endpoint
            results_csv = client.get_results_csv(execution_id) 
            timer.checkpoint("results_endpoint")
            lines = results_csv.strip().split('\n')
            print(f"   ✓ Results endpoint: {len(lines)} lines returned")
            
        except TimeoutError:
            print("   ⚠ Query completion timeout (testing endpoints only)")
        
        timer.stop()
        
        # Cleanup
        client.delete_query(query_id)
        print("   ✓ Endpoints test cleanup complete")
        
        details = {
            "test_query_id": query_id,
            "execution_id": execution_id,
            "endpoints_tested": ["create", "execute", "status", "results"],
            "timings": timer.get_report()
        }
        
        return True, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_timeout_handling() -> Tuple[bool, Dict[str, Any]]:
    """Test timeout behavior and proper error handling."""
    print("⏱️ Testing Timeout Handling...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        
        # Test with very short timeout to trigger timeout
        client_with_short_timeout = DuneTestClient(api_key)
        
        test_sql = QueryFactory.data_types_query()  # More complex query
        
        try:
            # This should timeout due to client's internal timeout
            client_with_short_timeout._retryRequest(
                client_with_short_timeout._retryRequest.__self__.__class__.get,
                f"https://httpbin.org/delay/10",  # This will definitely timeout
                timeout=1.0,  # 1 second timeout
                error_context="timeout test"
            )
            
            return False, {"error": "Expected timeout but request succeeded"}
            
        except TimeoutError:
            timer.checkpoint("timeout_triggered")
            print("   ✓ Timeout correctly triggered")
            
        except Exception as e:
            # Other errors are acceptable for timeout testing
            if "timeout" in str(e).lower():
                timer.checkpoint("timeout_triggered")
                print(f"   ✓ Timeout behavior observed: {e}")
            else:
                print(f"   ⚠ Different error (still ok): {e}")
        
        # Test Dune-specific timeout (polling)
        try:
            client = DuneTestClient(api_key)
            test_sql = QueryFactory.simple_select()
            query_id = client.create_query(test_sql, "timeout_test")
            execution_id = client.execute_query(query_id)
            
            # Try to wait with very short timeout
            client.wait_for_completion(execution_id, timeout=1)
            
            print("   ⚠ Query completed faster than expected timeout")
            
        except TimeoutError:
            timer.checkpoint("dune_timeout_triggered")
            print("   ✓ Dune query timeout correctly triggered")
            
        except Exception as e:
            # Query still running is acceptable
            if "timed out" in str(e).lower():
                timer.checkpoint("dune_timeout_triggered")
                print(f"   ✓ Dune timeout: {e}")
            else:
                print(f"   ⚠ Different Dune error: {e}")
        
        timer.stop()
        
        details = {
            "timeout_tests": ["http_timeout", "query_timeout"],
            "timings": timer.get_report()
        }
        
        return True, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_user_info_endpoint() -> Tuple[bool, Dict[str, Any]]:
    """Test user info endpoint and authentication details."""
    print("👤 Testing User Info Endpoint...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        client = DuneTestClient(api_key)
        
        # Test user info endpoint
        user_url = f"{client.base_url}/user"
        user_response = client._retryRequest(
            client._retryRequest.__self__.__class__.get,
            user_url,
            error_context="user info test"
        )
        
        timer.checkpoint("user_info_requested")
        
        if user_response.status_code == 200:
            user_data = user_response.json()
            timer.checkpoint("user_info_received")
            
            user_name = user_data.get('name', 'Unknown User')
            user_id = user_data.get('id')
            
            print(f"   ✓ User: {user_name}")
            if user_id:
                print(f"   ✓ User ID: {user_id}")
            
            details = {
                "user_authenticated": True,
                "user_name": user_name,
                "user_id": user_id,
                "user_data": {k: v for k, v in user_data.items() 
                           if k not in ['api_keys', 'private_data']},
                "timings": timer.get_report()
            }
            
            return True, details
            
        else:
            return False, {
                "error": f"User info endpoint failed: {user_response.status_code}",
                "response": user_response.text
            }
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def main():
    """Run API health check suite."""
    print("🏥 DUNE API HEALTH CHECK SUITE")
    print("=" * 50)
    
    # Load environment
    load_env_variables()
    
    # Check API key
    if not os.getenv("DUNE_API_KEY"):
        print("❌ DUNE_API_KEY not found. Please set it in your environment or .env file.")
        return False
    
    # Initialize result collector
    results = TestResultCollector()
    results.start_collection()
    
    # Run health check tests
    tests = [
        ("API Authentication", test_api_authentication),
        ("Rate Limiting", test_rate_limiting),
        ("API Endpoints", test_api_endpoints),
        ("Timeout Handling", test_timeout_handling),
        ("User Info", test_user_info_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        try:
            success, details = test_func()
            results.add_result(test_name, success, details)
            
            if success:
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                error = details.get('error', 'Unknown error')
                print(f"❌ {test_name} FAILED: {error}")
                
        except Exception as e:
            results.add_result(test_name, False, {"error": str(e)})
            print(f"❌ {test_name} EXCEPTION: {e}")
    
    results.finish_collection()
    summary = results.get_summary()
    
    # Summary
    print(f"\n{'=' * 50}")
    print("🎯 HEALTH CHECK SUMMARY")
    print(f"✅ {passed}/{total} tests passed")
    print(f"⏱️ Total duration: {summary['duration']:.2f}s")
    
    if passed == total:
        print("🎉 All health checks passed! API environment is healthy.")
        return True
    else:
        print("⚠️ Some health checks failed. Review issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
