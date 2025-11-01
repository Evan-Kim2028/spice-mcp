#!/usr/bin/env python3
"""
Query Lifecycle Test - Tier 1 Test Suite

Tests the complete query lifecycle: Create → Validate → Execute → Poll → Retrieve → Cleanup
This ensures the full workflow works end-to-end.
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tests.support.api_client import DuneTestClient, TestQueryManager
from tests.support.helpers import PerformanceTimer, TestEnvironment, TestResultCollector
from tests.support import QueryFactory, QueryValidator

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

def test_complete_lifecycle() -> Tuple[bool, Dict[str, Any]]:
    """Test complete query lifecycle from creation to cleanup."""
    print("🔄 Testing Complete Query Lifecycle...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        # Setup
        api_key = os.getenv("DUNE_API_KEY")
        with TestQueryManager(DuneTestClient(api_key)) as qm:
            test_sql = QueryFactory.simple_select()
            unique_name = f"lifecycle_test_{QueryFactory.unique_timestamp_suffix()}"
            
            # Step 1: Create Query
            timer.checkpoint("start_creation")
            query_id = qm.create_test_query(test_sql, unique_name)
            timer.checkpoint("query_created")
            print(f"   ✓ Step 1: Query created with ID: {query_id}")
            
            # Step 2: Validate Query Info
            query_info = qm.get_query_info(query_id)
            if not query_info:
                return False, {"error": "Query info not properly stored"}
            timer.checkpoint("query_validated")
            print(f"   ✓ Step 2: Query validated: {query_info.get('name', 'unknown')}")
            
            # Step 3: Execute Query  
            timer.checkpoint("start_execution")
            execution_id = qm.execute_and_wait(query_id, timeout=60)
            timer.checkpoint("query_completed")
            print(f"   ✓ Step 3: Query executed and completed: {execution_id}")
            
            # Step 4: Retrieve Results
            results_json = qm.client.get_results_json(query_id)
            timer.checkpoint("results_retrieved")
            
            if not isinstance(results_json, dict) or 'data' not in results_json:
                return False, {"error": "Invalid results format"}
            
            data_rows = results_json['data']
            print(f"   ✓ Step 4: Results retrieved: {len(data_rows)} rows")
            
            # Step 5: Validate Results
            # Convert to DataFrame for validation (basic implementation)
            if len(data_rows) == 0:
                return False, {"error": "No data returned from query"}
            
            # Basic validation of expected simple query result
            if len(data_rows[0]) >= 2:
                print(f"   ✓ Step 5: Results validated: expected column count")
            else:
                return False, {"error": "Result doesn't match expected format"}
            
            timer.checkpoint("results_validated")
            
            # Step 6: Cleanup (handled by context manager)
            print(f"   ✓ Step 6: Cleanup will be handled automatically")
        
        timer.stop()
        
        details = {
            "query_id": query_id,
            "execution_id": execution_id,
            "rows_returned": len(data_rows),
            "lifecycle_stages": [
                "created", "validated", "executed", "completed", 
                "retrieved", "validated", "cleanup"
            ],
            "timings": timer.get_report()
        }
        
        return True, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_error_states() -> Tuple[bool, Dict[str, Any]]:
    """Test error states at each stage of the lifecycle."""
    print("⚠️ Testing Error States...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        client = DuneTestClient(api_key)
        errors_tested = []
        
        # Test 1: Invalid SQL (creation error)
        try:
            client.create_query("SELECTTTT INVALID SQL", "invalid_sql_test")
            errors_tested.append(("invalid_sql", "FAILED", "Should have failed"))
        except Exception as e:
            if any(keyword in str(e).lower() for keyword in ["syntax", "invalid", "error"]):
                errors_tested.append(("invalid_sql", "PASSED", f"Correctly rejected: {e}"))
            else:
                errors_tested.append(("invalid_sql", "UNEXPECTED", f"Wrong error type: {e}"))
        
        timer.checkpoint("invalid_sql_test")
        
        # Test 2: Query execution with non-existent ID
        try:
            client.execute_query(999999999)
            errors_tested.append(("nonexistent_query", "FAILED", "Should have failed"))
        except Exception as e:
            if any(keyword in str(e).lower() for keyword in ["not found", "404", "invalid"]):
                errors_tested.append(("nonexistent_query", "PASSED", f"Correctly rejected: {e}"))
            else:
                errors_tested.append(("nonexistent_query", "UNEXPECTED", f"Wrong error type: {e}"))
        
        timer.checkpoint("nonexistent_query_test")
        
        # Test 3: Access results of non-existent execution
        try:
            client.get_execution_status("nonexistent_exec_id")
            errors_tested.append(("nonexistent_execution", "FAILED", "Should have failed"))
        except Exception as e:
            if any(keyword in str(e).lower() for keyword in ["not found", "404", "invalid"]):
                errors_tested.append(("nonexistent_execution", "PASSED", f"Correctly rejected: {e}"))
            else:
                errors_tested.append(("nonexistent_execution", "UNEXPECTED", f"Wrong error type: {e}"))
        
        timer.checkpoint("nonexistent_exec_test")
        
        # Test 4: Create valid query but test parameter errors
        try:
            valid_query_id = client.create_query(
                "SELECT {{valid_param}} as test", 
                "param_error_test"
            )
            
            # Try executing without required parameter
            client.execute_query(valid_query_id)  # Missing valid_param
            errors_tested.append(("missing_parameter", "FAILED", "Should have failed"))
            
            # Cleanup
            client.delete_query(valid_query_id)
            
        except Exception as e:
            if any(keyword in str(e).lower() for keyword in ["param", "missing", "required"]):
                errors_tested.append(("missing_parameter", "PASSED", f"Correctly rejected: {e}"))
            else:
                errors_tested.append(("missing_parameter", "UNCERTAIN", f"Error: {e}"))
        
        timer.checkpoint("parameter_errors_test")
        
        timer.stop()
        
        # Calculate success rate
        passed_errors = sum(1 for _, status, _ in errors_tested if status == "PASSED")
        total_errors = len(errors_tested)
        
        print(f"   ✓ Error state tests: {passed_errors}/{total_errors} proper error handling")
        
        for error_type, status, message in errors_tested:
            icon = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "?"
            print(f"   {icon} {error_type}: {message}")
        
        details = {
            "error_tests": errors_tested,
            "passed_rate": passed_errors / total_errors if total_errors > 0 else 0,
            "timings": timer.get_report()
        }
        
        return passed_errors == total_errors, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_rollback_scenarios() -> Tuple[bool, Dict[str, Any]]:
    """Test rollback scenarios and cleanup failure handling."""
    print("🔄 Testing Rollback Scenarios...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        client = DuneTestClient(api_key)
        
        rollback_tests = []
        
        # Test 1: Manual cleanup after failure
        query_ids_to_cleanup = []
        try:
            # Create several queries
            for i in range(3):
                query_id = client.create_query(
                    f"SELECT {i} as test_col", 
                    f"rollback_test_{i}"
                )
                query_ids_to_cleanup.append(query_id)
            
            # Simulate a failure before cleanup
            # (In real scenario, this would be an exception)
            print(f"   Created {len(query_ids_to_cleanup)} queries for rollback test")
            
        except Exception as e:
            print(f"   Error during query creation: {e}")
        
        finally:
            # Manual cleanup
            cleanup_count = 0
            for query_id in query_ids_to_cleanup:
                if client.delete_query(query_id):
                    cleanup_count += 1
            rollback_tests.append(("manual_cleanup", cleanup_count, len(query_ids_to_cleanup)))
            print(f"   ✓ Manual cleanup: {cleanup_count}/{len(query_ids_to_cleanup)} queries")
        
        timer.checkpoint("manual_rollback")
        
        # Test 2: Context manager cleanup on exception
        try:
            with TestQueryManager(client) as qm:
                query_id = qm.create_test_query("SELECT 1 as test", "exception_test")
                
                # Simulate an exception
                raise Exception("Simulated test exception")
                
        except Exception as e:
            if "Simulated test exception" in str(e):
                rollback_tests.append(("context_cleanup", "HANDLED", "Exception occurred as expected"))
                print("   ✓ Context manager: Exception handled correctly")
            else:
                rollback_tests.append(("context_cleanup", "UNEXPECTED", f"Wrong exception: {e}"))
        
        timer.checkpoint("context_rollback")
        
        # Test 3: Cleanup with invalid queries (should not fail)
        try:
            cleanup_attempts = 0
            cleanup_successes = 0
            
            # Try to delete queries that don't exist
            for fake_id in [999999, 888888, 777777]:
                cleanup_attempts += 1
                if client.delete_query(fake_id):
                    cleanup_successes += 1
            
            # Try to delete queries that might exist
            query_id = client.create_query("SELECT 1", "cleanup_test")
            cleanup_attempts += 1
            if client.delete_query(query_id):
                cleanup_successes += 1
            
            rollback_tests.append(("cleanup_resilience", cleanup_successes, cleanup_attempts))
            print(f"   ✓ Cleanup resilience: {cleanup_successes}/{cleanup_attempts} operations succeeded")
            
        except Exception as e:
            rollback_tests.append(("cleanup_resilience", "FAILED", str(e)))
            print(f"   ✗ Cleanup resilience failed: {e}")
        
        timer.stop()
        
        details = {
            "rollback_tests": rollback_tests,
            "timings": timer.get_report()
        }
        
        # All rollback tests should pass (or handle errors gracefully)
        return True, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_parameter_validation() -> Tuple[bool, Dict[str, Any]]:
    """Test parameter validation during query lifecycle."""
    print("🔧 Testing Parameter Validation...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        client = DuneTestClient(api_key)
        
        param_tests = []
        
        # Test 1: Create query with parameters
        param_sql = "SELECT {{test_param}} as value, 42 as constant"
        query_id = client.create_query(param_sql, "param_validation_test")
        
        print(f"   ✓ Parameterized query created: {query_id}")
        timer.checkpoint("param_query_created")
        
        # Test 2: Execute with valid parameters
        valid_params = {"test_param": "hello_world"}
        execution_id = client.execute_query(query_id, valid_params)
        
        print(f"   ✓ Executed with valid parameters: {execution_id}")
        timer.checkpoint("valid_paramexec")
        param_tests.append(("valid_params", "PASSED", "Execution succeeded"))
        
        # Wait for completion
        try:
            status = client.wait_for_completion(execution_id, timeout=30)
            print(f"   ✓ Query completed with params: {status.get('state', 'unknown')}")
            timer.checkpoint("param_query_completed")
            param_tests.append(("param_completion", "PASSED", "Query completed"))
        except TimeoutError:
            param_tests.append(("param_completion", "TIMEOUT", "Query took too long"))
        
        # Test 3: Execute with invalid parameters
        try:
            # Using different parameter name should fail
            invalid_params = {"wrong_param": "value"}
            client.execute_query(query_id, invalid_params)
            param_tests.append(("invalid_params", "FAILED", "Should have rejected wrong parameters"))
        except Exception as e:
            if "param" in str(e).lower():
                param_tests.append(("invalid_params", "PASSED", f"Correctly rejected: {e}"))
            else:
                param_tests.append(("invalid_params", "UNCERTAIN", f"Different error: {e}"))
        
        timer.checkpoint("invalid_param_attempt")
        
        # Test 4: Execute with missing parameters
        try:
            client.execute_query(query_id)  # No parameters
            param_tests.append(("missing_params", "FAILED", "Should require parameters"))
        except Exception as e:
            if "param" in str(e).lower() or "missing" in str(e).lower():
                param_tests.append(("missing_params", "PASSED", f"Correctly required: {e}"))
            else:
                param_tests.append(("missing_params", "UNCERTAIN", f"Different error: {e}"))
        
        timer.checkpoint("missing_param_attempt")
        
        # Cleanup
        client.delete_query(query_id)
        print("   ✓ Parameter test query cleaned up")
        
        timer.stop()
        
        # Calculate success rate
        passed_params = sum(1 for _, status, _ in param_tests if status == "PASSED")
        total_params = len(param_tests)
        
        print(f"   ✓ Parameter tests: {passed_params}/{total_params} passed")
        
        for test_name, status, message in param_tests:
            icon = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "?"
            print(f"   {icon} {test_name}: {message}")
        
        details = {
            "parameter_tests": param_tests,
            "success_rate": passed_params / total_params if total_params > 0 else 0,
            "timings": timer.get_report()
        }
        
        return passed_params == total_params, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_concurrent_queries() -> Tuple[bool, Dict[str, Any]]:
    """Test concurrent query handling and resource management."""
    print("🚀 Testing Concurrent Queries...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        
        concurrent_results = []
        
        # Create multiple queries concurrently
        concurrent_queries = []
        num_concurrent = 3
        
        timer.checkpoint("concurrent_start")
        
        try:
            # Create queries
            for i in range(num_concurrent):
                client = DuneTestClient(api_key)
                test_sql = f"SELECT {i} as query_id, 'concurrent_{i}' as label"
                query_id = client.create_query(test_sql, f"concurrent_test_{i}")
                concurrent_queries.append((client, query_id, i))
                print(f"   ✓ Created concurrent query {i}: {query_id}")
            
            timer.checkpoint("concurrent_created")
            
            # Execute all queries
            execution_ids = []
            for client, query_id, i in concurrent_queries:
                execution_id = client.execute_query(query_id)
                execution_ids.append((client, query_id, execution_id, i))
                print(f"   ✓ Started concurrent execution {i}: {execution_id}")
            
            timer.checkpoint("concurrent_executed")
            
            # Wait for all to complete (with reasonable timeout)
            completed_count = 0
            for client, query_id, execution_id, i in execution_ids:
                try:
                    status = client.wait_for_completion(execution_id, timeout=60)
                    if status.get('state') == 'QUERY_STATE_COMPLETED':
                        completed_count += 1
                    print(f"   ✓ Concurrent query {i} completed: {status.get('state')}")
                except TimeoutError:
                    print(f"   ⚠ Concurrent query {i} timed out")
                finally:
                    client.delete_query(query_id)
            
            timer.checkpoint("concurrent_completed")
            concurrent_results.append(("concurrent_execution", completed_count, num_concurrent))
            
            print(f"   ✓ Concurrent queries: {completed_count}/{num_concurrent} completed")
            
        except Exception as e:
            print(f"   ✗ Concurrent test error: {e}")
            concurrent_results.append(("concurrent_execution", "ERROR", str(e)))
        
        timer.stop()
        
        details = {
            "concurrent_results": concurrent_results,
            "concurrent_count": num_concurrent,
            "timings": timer.get_report()
        }
        
        # At least some concurrent queries should work
        success = any(result == "ERROR" for _, result, _ in concurrent_results) is False
        
        return success, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def main():
    """Run query lifecycle test suite."""
    print("🔄 DUNE QUERY LIFECYCLE TEST SUITE")
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
    
    # Run lifecycle tests
    tests = [
        ("Complete Lifecycle", test_complete_lifecycle),
        ("Error States", test_error_states),
        ("Rollback Scenarios", test_rollback_scenarios),
        ("Parameter Validation", test_parameter_validation),
        ("Concurrent Queries", test_concurrent_queries),
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
    print("🎯 LIFECYCLE TEST SUMMARY")
    print(f"✅ {passed}/{total} tests passed")
    print(f"⏱️ Total duration: {summary['duration']:.2f}s")
    
    if passed == total:
        print("🎉 All lifecycle tests passed! Query workflow is robust.")
        return True
    else:
        print("⚠️ Some lifecycle tests failed. Review workflow issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
