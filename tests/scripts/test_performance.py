#!/usr/bin/env python3
"""
Performance Test - Tier 2 Test Suite

Tests performance characteristics, benchmarks, and resource usage.
Ensures the system meets performance requirements and identifies bottlenecks.
"""
import os
import sys
import time
import json
import psutil
import threading
from pathlib import Path
from typing import Dict, Any, Tuple, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tests.support.api_client import DuneTestClient, TestQueryManager
from tests.support.helpers import PerformanceTimer, TestResultCollector, TestEnvironment
from tests.support import QueryFactory, ExpectedResults

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

def get_resource_usage() -> Dict[str, float]:
    """Get current system resource usage."""
    process = psutil.Process()
    return {
        'cpu_percent': process.cpu_percent(),
        'memory_mb': process.memory_info().rss / 1024 / 1024,
        'memory_percent': process.memory_percent(),
        'open_files': len(process.open_files()),
        'threads': process.num_threads()
    }

def test_query_execution_benchmarks() -> Tuple[bool, Dict[str, Any]]:
    """Benchmark query execution times against expected performance."""
    print("⏱️ Testing Query Execution Benchmarks...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        initial_resources = get_resource_usage()
        
        api_key = os.getenv("DUNE_API_KEY")
        benchmarks = []
        
        # Test different query types with performance expectations
        test_cases = [
            ("simple_query", QueryFactory.simple_select(), 10.0),
            ("data_types_query", QueryFactory.data_types_query(), 15.0),
            ("aggregate_query", QueryFactory.aggregate_query(), 20.0),
            ("time_series_query", QueryFactory.time_series_query(), 25.0),
        ]
        
        with TestQueryManager(DuneTestClient(api_key)) as qm:
            for test_name, test_sql, expected_max_time in test_cases:
                test_timer = PerformanceTimer()
                test_timer.start()
                
                print(f"   Testing {test_name}...")
                
                # Create query
                query_id = qm.create_test_query(test_sql, f"perf_test_{test_name}")
                test_timer.checkpoint("query_created")
                
                # Execute query
                execution_id = qm.execute_and_wait(query_id, timeout=expected_max_time * 2)
                test_timer.checkpoint("query_completed")
                
                # Get results
                results_json = qm.client.get_results_json(query_id)
                rows_returned = len(results_json.get('data', []))
                test_timer.checkpoint("results_retrieved")
                
                # Stop timer
                test_timer.stop()
                duration = test_timer.duration
                
                # Check performance
                passes_benchmark = duration <= expected_max_time
                benchmarks.append({
                    'test_name': test_name,
                    'duration': duration,
                    'expected_max_time': expected_max_time,
                    'passes_benchmark': passes_benchmark,
                    'rows_returned': rows_returned,
                    'performance_ratio': duration / expected_max_time
                })
                
                status = "✓" if passes_benchmark else "✗"
                print(f"   {status} {test_name}: {duration:.2f}s (expected: ≤{expected_max_time}s)")
            
            final_resources = get_resource_usage()
            timer.stop()
            
            # Analyze results
            passed_benchmarks = sum(1 for b in benchmarks if b['passes_benchmark'])
            total_benchmarks = len(benchmarks)
            avg_performance_ratio = sum(b['performance_ratio'] for b in benchmarks) / total_benchmarks
            
            print(f"   Benchmarks: {passed_benchmarks}/{total_benchmarks} within expected time")
            print(f"   Average performance ratio: {avg_performance_ratio:.2f} (1.0 = optimal)")
            print(f"   Memory delta: {final_resources['memory_mb'] - initial_resources['memory_mb']:.1f} MB")
        
        details = {
            "benchmarks": benchmarks,
            "passed_benchmarks": passed_benchmarks,
            "total_benchmarks": total_benchmarks,
            "avg_performance_ratio": avg_performance_ratio,
            "resource_usage": {
                "initial": initial_resources,
                "final": final_resources,
                "memory_delta": final_resources['memory_mb'] - initial_resources['memory_mb']
            },
            "timings": timer.get_report()
        }
        
        # At least 80% of benchmarks should pass
        return passed_benchmarks >= total_benchmarks * 0.8, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_concurrent_query_limits() -> Tuple[bool, Dict[str, Any]]:
    """Test concurrent query handling and identify limits."""
    print("🚀 Testing Concurrent Query Limits...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        
        # Test different concurrency levels
        concurrency_levels = [1, 2, 3]  # Conservative to avoid rate limiting
        concurrent_results = []
        
        for concurrent_count in concurrency_levels:
            print(f"   Testing {concurrent_count} concurrent queries...")
            
            concurrent_timer = PerformanceTimer()
            concurrent_timer.start()
            
            results = []
            exceptions = []
            
            def run_single_query(index):
                try:
                    client = DuneTestClient(api_key)
                    test_sql = f"SELECT {index} as query_index, 'concurrent_test' as label"
                    
                    with TestQueryManager(client) as qm:
                        query_id = qm.create_test_query(test_sql, f"concurrent_{index}_{int(time.time())}")
                        execution_id = qm.execute_and_wait(query_id, timeout=60)
                        results_json = qm.client.get_results_json(query_id)
                        
                        return {
                            'index': index,
                            'query_id': query_id,
                            'execution_id': execution_id,
                            'success': True,
                            'rows': len(results_json.get('data', []))
                        }
                        
                except Exception as e:
                    exceptions.append({'index': index, 'error': str(e)})
                    return {
                        'index': index,
                        'success': False,
                        'error': str(e)
                    }
            
            # Execute queries concurrently
            with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
                futures = [executor.submit(run_single_query, i) for i in range(concurrent_count)]
                
                try:
                    for future in futures:
                        result = future.result(timeout=120)  # 2 minute timeout per query
                        results.append(result)
                        
                except FutureTimeoutError:
                    exceptions.append({'error': 'Query execution timeout'})
                except Exception as e:
                    exceptions.append({'error': f'Thread execution error: {e}'})
            
            concurrent_timer.stop()
            
            # Analyze concurrent execution
            successful_queries = [r for r in results if r.get('success', False)]
            failed_queries = exceptions
            
            concurrent_results.append({
                'concurrent_count': concurrent_count,
                'successful_count': len(successful_queries),
                'failed_count': len(failed_queries),
                'success_rate': len(successful_queries) / concurrent_count,
                'duration': concurrent_timer.duration,
                'results': results,
                'exceptions': failed_queries
            })
            
            print(f"   ✓ {concurrent_count} concurrent: {len(successful_queries)}/{concurrent_count} success")
            if failed_queries:
                print(f"   ⚠ Errors: {len(failed_queries)} failed queries")
        
        timer.stop()
        
        # Find optimal concurrency level
        success_rates = [r['success_rate'] for r in concurrent_results]
        max_successful = max(success_rates) if success_rates else 0
        optimal_concurrency = next(
            (r['concurrent_count'] for r in concurrent_results if r['success_rate'] == max_successful),
            1
        )
        
        details = {
            "concurrent_results": concurrent_results,
            "optimal_concurrency": optimal_concurrency,
            "max_success_rate": max_successful,
            "recommended_concurrent_limit": optimal_concurrency,
            "timings": timer.get_report()
        }
        
        # Should handle at least basic concurrency (1 query) without issues
        return max_successful >= 0.5, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_memory_usage_patterns() -> Tuple[bool, Dict[str, Any]]:
    """Test memory usage patterns and detect potential leaks."""
    print("💾 Testing Memory Usage Patterns...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        memory_snapshots = []
        
        # Baseline memory usage
        baseline_memory = get_resource_usage()
        memory_snapshots.append({
            'phase': 'baseline',
            'memory_mb': baseline_memory['memory_mb'],
            'timestamp': time.time()
        })
        
        # Perform multiple queries and track memory
        query_count = 5
        stress_query = QueryFactory.data_types_query()
        
        with TestQueryManager(DuneTestClient(api_key)) as qm:
            for i in range(query_count):
                print(f"   Memory test query {i+1}/{query_count}...")
                
                # Create and execute query
                query_id = qm.create_test_query(stress_query, f"memory_test_{i}")
                execution_id = qm.execute_and_wait(query_id, timeout=60)
                results_json = qm.client.get_results_json(query_id)
                
                # Take memory snapshot
                current_memory = get_resource_usage()
                memory_snapshots.append({
                    'phase': f'query_{i+1}',
                    'memory_mb': current_memory['memory_mb'],
                    'timestamp': time.time(),
                    'rows_processed': len(results_json.get('data', []))
                })
                
                # Small delay to allow for GC
                time.sleep(0.5)
        
        # Final memory snapshot
        final_memory = get_resource_usage()
        memory_snapshots.append({
            'phase': 'final',
            'memory_mb': final_memory['memory_mb'],
            'timestamp': time.time()
        })
        
        timer.stop()
        
        # Analyze memory patterns
        baseline_mb = baseline_memory['memory_mb']
        peak_mb = max(snapshot['memory_mb'] for snapshot in memory_snapshots)
        final_mb = final_memory['memory_mb']
        
        memory_increase = final_mb - baseline_mb
        memory_growth_rate = memory_increase / baseline_mb if baseline_mb > 0 else 0
        
        # Check for memory leak indicators
        memory_ok = True
        issues = []
        
        if memory_growth_rate > 0.5:  # More than 50% growth
            issues.append(f"High memory growth: {memory_growth_rate:.1%}")
            memory_ok = False
        
        if memory_increase > 100:  # More than 100MB growth
            issues.append(f"Large memory increase: {memory_increase:.1f}MB")
            memory_ok = False
        
        # Check memory stability over queries
        query_memories = [s for s in memory_snapshots if s['phase'].startswith('query_')]
        if len(query_memories) > 1:
            memory_trend = query_memories[-1]['memory_mb'] - query_memories[0]['memory_mb']
            if memory_trend > 50:  # Growing trend during queries
                issues.append(f"Memory growth during queries: {memory_trend:.1f}MB")
                memory_ok = False
        
        print(f"   Baseline memory: {baseline_mb:.1f} MB")
        print(f"   Peak memory: {peak_mb:.1f} MB")
        print(f"   Final memory: {final_mb:.1f} MB")
        print(f"   Memory increase: {memory_increase:.1f} MB ({memory_growth_rate:.1%})")
        
        if memory_ok:
            print("   ✓ Memory usage appears stable")
        else:
            print(f"   ⚠ Memory issues detected: {', '.join(issues)}")
        
        details = {
            "memory_snapshots": memory_snapshots,
            "baseline_memory_mb": baseline_mb,
            "peak_memory_mb": peak_mb,
            "final_memory_mb": final_mb,
            "memory_increase_mb": memory_increase,
            "memory_growth_rate": memory_growth_rate,
            "memory_ok": memory_ok,
            "issues": issues,
            "timings": timer.get_report()
        }
        
        return memory_ok, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_timeout_behavior() -> Tuple[bool, Dict[str, Any]]:
    """Test timeout behavior at different levels."""
    print("⏰ Testing Timeout Behavior...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        timeout_tests = []
        
        # Test 1: Client-level timeout
        print("   Testing client-level timeout...")
        client_timer = PerformanceTimer()
        client_timer.start()
        
        try:
            # Create client with very short timeout
            short_timeout_client = DuneTestClient(api_key)
            simple_sql = QueryFactory.simple_select()
            
            query_id = short_timeout_client.create_query(simple_sql, "timeout_test_1")
            
            # This should work fine (creation is fast)
            timeout_tests.append({
                'test_type': 'client_creation',
                'success': True,
                'timeout_set': 'short',
                'result': 'succeeded'
            })
            
            # Execute with reasonable timeout
            execution_id = short_timeout_client.execute_query(query_id)
            timeout_tests.append({
                'test_type': 'client_execution',
                'success': True,
                'timeout_set': 'short',
                'result': 'executed'
            })
            
            # Wait with short timeout (should timeout)
            try:
                short_timeout_client.wait_for_completion(execution_id, timeout=1)
                timeout_tests.append({
                    'test_type': 'client_wait_short',
                    'success': False,
                    'timeout_set': 'short',
                    'result': 'unexpected_success'
                })
            except TimeoutError:
                timeout_tests.append({
                    'test_type': 'client_wait_short',
                    'success': True,
                    'timeout_set': 'short',
                    'result': 'timeout_as_expected'
                })
            
            # Cleanup
            short_timeout_client.delete_query(query_id)
            
        except Exception as e:
            timeout_tests.append({
                'test_type': 'client_short_timeout',
                'success': False,
                'error': str(e)
            })
        
        client_timer.stop()
        
        # Test 2: Query performance levels
        print("   Testing performance level timeouts...")
       绩效测试 = ['medium', 'large']  # Skip 'low' for reliability
        
        for performance in 绩效测试:
            perf_timer = PerformanceTimer()
            perf_timer.start()
            
            try:
                with TestQueryManager(DuneTestClient(api_key)) as qm:
                    test_sql = QueryFactory.aggregate_query()
                    query_id = qm.create_test_query(test_sql, f"perf_{performance}")
                    
                    # Execute with different performance levels
                    execution_id = qm.client.execute_query(query_id, performance=performance)
                    status = qm.client.wait_for_completion(execution_id, timeout=45)
                    
                    perf_timer.stop()
                    
                    timeout_tests.append({
                        'test_type': f'performance_{performance}',
                        'success': True,
                        'duration': perf_timer.duration,
                        'state': status.get('state', 'unknown')
                    })
                    
                    print(f"   ✓ Performance {performance}: {perf_timer.duration:.2f}s")
                    
            except TimeoutError:
                perf_timer.stop()
                timeout_tests.append({
                    'test_type': f'performance_{performance}',
                    'success': False,
                    'duration': perf_timer.duration,
                    'result': 'timeout'
                })
                print(f"   ⚠ Performance {performance}: timeout after {perf_timer.duration:.2f}s")
                
            except Exception as e:
                perf_timer.stop()
                timeout_tests.append({
                    'test_type': f'performance_{performance}',
                    'success': False,
                    'duration': perf_timer.duration,
                    'error': str(e)
                })
                print(f"   ✗ Performance {performance}: error - {e}")
        
        timer.stop()
        
        # Analyze timeout behavior
        successful_timeouts = sum(1 for t in timeout_tests 
                                if t.get('success') or t.get('result') == 'timeout_as_expected')
        total_timeouts = len(timeout_tests)
        
        timeout_behavior_ok = successful_timeouts >= total_timeouts * 0.7
        
        print(f"   Timeout behavior: {successful_timeouts}/{total_timeouts} handled correctly")
        
        details = {
            "timeout_tests": timeout_tests,
            "successful_timeouts": successful_timeouts,
            "total_timeouts": total_timeouts,
            "timeout_behavior_ok": timeout_behavior_ok,
            "timings": timer.get_report()
        }
        
        return timeout_behavior_ok, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_rate_limiting_behavior() -> Tuple[bool, Dict[str, Any]]:
    """Test rate limiting behavior and backoff mechanisms."""
    print("🚦 Testing Rate Limiting Behavior...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        
        # Test rapid succession requests
        print("   Testing ratelimit with rapid requests...")
        rapid_timer = PerformanceTimer()
        rapid_timer.start()
        
        client = DuneTestClient(api_key)
        test_sql = QueryFactory.simple_select()
        request_times = []
        rate_limit_detected = False
        
        try:
            for i in range(8):  # Make several rapid requests
                req_start = time.time()
                
                query_id = client.create_query(f"{test_sql} -- rapid {i}", f"rapid_test_{i}")
                
                req_end = time.time()
                duration = req_end - req_start
                request_times.append(duration)
                
                # Clean up
                client.delete_query(query_id)
                
                print(f"     Request {i+1}: {duration:.3f}s")
                
                # Check for rate limiting indicators
                if duration > 2.0:  # Significantly slower than normal
                    rate_limit_detected = True
                
                # Small delay between requests
                time.sleep(0.2)
                
        except Exception as e:
            if "rate limit" in str(e).lower():
                rate_limit_detected = True
                print(f"   ✓ Rate limiting detected: {e}")
            else:
                print(f"   ✗ Unexpected error during rapid requests: {e}")
        
        rapid_timer.stop()
        
        # Analyze request patterns
        if request_times:
            avg_time = sum(request_times) / len(request_times)
            max_time = max(request_times)
            min_time = min(request_times)
            
            # Rate limiting indicators
            time_variance = max_time - min_time
            high_variance = time_variance > avg_time  # High variance suggests throttling
            
            rate_limit_analysis = {
                'request_count': len(request_times),
                'avg_time': avg_time,
                'min_time': min_time,
                'max_time': max_time,
                'time_variance': time_variance,
                'rate_limit_detected': rate_limit_detected or high_variance
            }
        else:
            rate_limit_analysis = {'error': 'No requests completed'}
        
        timer.stop()
        
        # Rate limiting behavior is considered OK if we don't get hard failures
        rate_limiting_ok = len(request_times) >= 5  # At least some requests should work
        
        print(f"   Requests completed: {len(request_times)}/8")
        print(f"   Rate limiting OK: {rate_limiting_ok}")
        
        details = {
            "rate_limit_analysis": rate_limit_analysis,
            "request_times": request_times,
            "rate_limiting_ok": rate_limiting_ok,
            "timings": timer.get_report()
        }
        
        return rate_limiting_ok, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def main():
    """Run performance test suite."""
    print("⏱️ DUNE PERFORMANCE TEST SUITE")
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
    
    # Run performance tests
    tests = [
        ("Query Execution Benchmarks", test_query_execution_benchmarks),
        ("Concurrent Query Limits", test_concurrent_query_limits),
        ("Memory Usage Patterns", test_memory_usage_patterns),
        ("Timeout Behavior", test_timeout_behavior),
        ("Rate Limiting Behavior", test_rate_limiting_behavior),
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
    print("🎯 PERFORMANCE TEST SUMMARY")
    print(f"✅ {passed}/{total} tests passed")
    print(f"⏱️ Total duration: {summary['duration']:.2f}s")
    
    if passed >= total * 0.8:  # 80% pass rate for performance tests
        print("🎉 Performance tests passed! System meets performance requirements.")
        return True
    else:
        print("⚠️ Some performance tests failed. Review bottlenecks and resource usage.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
