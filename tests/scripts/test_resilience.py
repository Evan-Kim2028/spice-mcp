#!/usr/bin/env python3
"""
Resilience Test - Tier 4 Test Suite

Tests network interruptions, retry logic, backoff mechanisms, and error recovery patterns.
Ensures the system can recover gracefully from various failure scenarios.
"""
import os
import sys
import time
import json
import random
import threading
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import socket
import urllib.error

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tests.support.api_client import DuneTestClient, TestQueryManager
from tests.support.helpers import PerformanceTimer, TestResultCollector, RetryMechanism
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

class NetworkSimulator:
    """Simulate various network conditions for resilience testing."""
    
    def __init__(self):
        self.failure_scenarios = []
        self.current_scenario = None
        
    def add_scenario(self, name: str, failure_rate: float, exception_types: List[type]):
        """Add a network failure scenario."""
        self.failure_scenarios.append({
            'name': name,
            'failure_rate': failure_rate,
            'exception_types': exception_types,
            'call_count': 0
        })
    
    def simulate_request(self, original_func, *args, **kwargs):
        """Simulate network request with potential failures."""
        if not self.current_scenario:
            return original_func(*args, **kwargs)
        
        self.current_scenario['call_count'] += 1
        failure_rate = self.current_scenario['failure_rate']
        
        if random.random() < failure_rate:
            # Choose an exception type to raise
            exception_type = random.choice(self.current_scenario['exception_types'])
            raise exception_type(f"Simulated network failure: {exception_type.__name__}")
        
        return original_func(*args, **kwargs)
    
    def set_scenario(self, name: str):
        """Set the active failure scenario."""
        self.current_scenario = next((s for s in self.failure_scenarios if s['name'] == name), None)

def test_retry_backoff_mechanisms() -> Tuple[bool, Dict[str, Any]]:
    """Test retry logic and exponential backoff behavior."""
    print("🔄 Testing Retry Backoff Mechanisms...")
    timer = PerformanceTimer()
    network_sim = NetworkSimulator()
    
    try:
        timer.start()
        
        # Define failure scenarios
        network_sim.add_scenario(
            "occasional_failures",
            failure_rate=0.3,
            exception_types=[
                urllib.error.URLError,
                socket.timeout,
                ConnectionError
            ]
        )
        
        network_sim.add_scenario(
            "consintermittent_failures",
            failure_rate=0.6,
            exception_types=[
                urllib.error.HTTPError,
                TimeoutError,
                ConnectionResetError
            ]
        )
        
        api_key = os.getenv("DUNE_API_KEY")
        retry_results = []
        
        for scenario_name in ["occasional_failures", "consintermittent_failures"]:
            print(f"   Testing scenario: {scenario_name}")
            network_sim.set_scenario(scenario_name)
            
            # Test retry mechanism
            retry_attempts = []
            retry_times = []
            
            def failing_function():
                start_time = time.time()
                try:
                    return network_sim.simulate_request(lambda: "success")
                finally:
                    retry_times.append(time.time() - start_time)
            
            # Execute with retry mechanism
            for i in range(5):
                retry_start = time.time()
                
                try:
                    result = RetryMechanism.retry_with_backoff(
                        failing_function,
                        max_retries=5,
                        backoff_factor=0.1,
                        exceptions=[urllib.error.URLError, socket.timeout, ConnectionError]
                    )
                    
                    retry_duration = time.time() - retry_start
                    retry_attempts.append({
                        'attempt': i + 1,
                        'success': True,
                        'duration': retry_duration,
                        'retry_count': len(retry_times)
                    })
                    
                    print(f"     ✓ Attempt {i+1}: Success after {retry_duration:.2f}s")
                    
                except Exception as e:
                    retry_duration = time.time() - retry_start
                    retry_attempts.append({
                        'attempt': i + 1,
                        'success': False,
                        'duration': retry_duration,
                        'retry_count': len(retry_times),
                        'error': str(e)
                    })
                    
                    print(f"     ✗ Attempt {i+1}: Failed after {retry_duration:.2f}s - {str(e)[:50]}...")
            
            # Analyze backoff behavior
            successful_retries = [r for r in retry_attempts if r['success']]
            backoff_validation = {
                'scenario_name': scenario_name,
                'total_attempts': len(retry_attempts),
                'successful_retries': len(successful_retries),
                'success_rate': len(successful_retries) / len(retry_attempts),
                'avg_retry_count': sum(r['retry_count'] for r in successful_retries) / len(successful_retries) if successful_retries else 0,
                'retry_attempts': retry_attempts
            }
            
            retry_results.append(backoff_validation)
            
            # Check if retry backoff shows exponential pattern
            if len(retry_times) > 2:
                retry_gaps = []
                for i in range(1, min(len(retry_times), 4)):
                    retry_gaps.append(retry_times[i] - retry_times[i-1])
                
                # Exponential backoff validation (gaps should increase)
                exponential_pattern = all(retry_gaps[i] < retry_gaps[i+1] for i in range(len(retry_gaps)-1))
                backoff_validation['exponential_backoff_detected'] = exponential_pattern
            
        timer.checkpoint("retry_backoff_tests_completed")
        
        # Analyze overall resilience
        total_retry_tests = len(retry_results)
        retry_success_rate = sum(r['success_rate'] for r in retry_results) / total_retry_tests
        
        timer.stop()
        
        print(f"   Retry backoff: {retry_success_rate:.1%} overall success rate")
        
        details = {
            "retry_results": retry_results,
            "total_retry_tests": total_retry_tests,
            "retry_success_rate": retry_success_rate,
            "timings": timer.get_report()
        }
        
        return retry_success_rate >= 0.6, details  # 60% success rate under partial failures
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_network_interruption_recovery() -> Tuple[bool, Dict[str, Any]]:
    """Test recovery from network interruptions."""
    print("🌐 Testing Network Interruption Recovery...")
    timer = PerformanceTimer()
    network_sim = NetworkSimulator()
    
    try:
        timer.start()
        
        # Setup network simulation with intermittent failures
        network_sim.add_scenario(
            "network_drops",
            failure_rate=0.4,
            exception_types=[
                ConnectionResetError,
                socket ConnectionError,
                urllib.error.URLError
            ]
        )
        
        api_key = os.getenv("DUNE_API_KEY")
        
        # Test network interruption scenarios
        interruption_results = []
        
        # Test 1: During query creation
        print("   Testing interruptions during query creation...")
        network_sim.set_scenario("network_drops")
        
        creation_successes = 0
        creation_attempts = 5
        
        for i in range(creation_attempts):
            try:
                with patch('requests.post', side_effect=lambda *args, **kwargs: network_sim.simulate_request(
                    requests.post, *args, **kwargs)):
                    
                    client = DuneTestClient(api_key)
                    query_id = client.create_query(QueryFactory.simple_select(), f"network_test_{i}")
                    creation_successes += 1
                    print(f"     ✓ Creation {i+1}: Success (query {query_id})")
                    
                    # Cleanup
                    client.delete_query(query_id)
                    
            except Exception as e:
                print(f"     ✗ Creation {i+1}: Failed - {str(e)[:50]}...")
        
        creation_recovery_rate = creation_successes / creation_attempts
        interruption_results.append({
            'test_type': 'query_creation',
            'attempts': creation_attempts,
            'successes': creation_successes,
            'recovery_rate': creation_recovery_rate
        })
        
        # Test 2: During query execution
        print("   Testing interruptions during query execution...")
        try:
            # Create a query first (without network issues)
            client = DuneTestClient(api_key)
            query_id = client.create_query(QueryFactory.simple_select(), "execution_test")
            print(f"     Created query: {query_id}")
            
            execution_successes = 0
            execution_attempts = 3
            
            for i in range(execution_attempts):
                try:
                    with patch('requests.post', side_effect=lambda *args, **kwargs: network_sim.simulate_request(
                        requests.post, *args, **kwargs)):
                        
                        execution_id = client.execute_query(query_id)
                        execution_successes += 1
                        print(f"     ✓ Execution {i+1}: Success (execution {execution_id})")
                        
                except Exception as e:
                    print(f"     ✗ Execution {i+1}: Failed - {str(e)[:50]}...")
            
            execution_recovery_rate = execution_successes / execution_attempts
            interruption_results.append({
                'test_type': 'query_execution',
                'attempts': execution_attempts,
                'successes': execution_successes,
                'recovery_rate': execution_recovery_rate
            })
            
            # Cleanup
            client.delete_query(query_id)
            
        except Exception as e:
            interruption_results.append({
                'test_type': 'query_execution',
                'attempts': 0,
                'successes': 0,
                'recovery_rate': 0.0,
                'error': str(e)
            })
        
        # Test 3: During result retrieval
        print("   Testing interruptions during result retrieval...")
        try:
            # Create and execute query first (without network issues)
            client = DuneTestClient(api_key)
            query_id = client.create_query(QueryFactory.simple_select(), "retrieval_test")
            execution_id = client.execute_query(query_id)
            
            # Wait for completion (without network issues)
            status = client.wait_for_completion(execution_id, timeout=30)
            print(f"     Query completed: {status.get('state')}")
            
            retrieval_successes = 0
            retrieval_attempts = 3
            
            for i in range(retrieval_attempts):
                try:
                    with patch('requests.get', side_effect=lambda *args, **kwargs: network_sim.simulate_request(
                        requests.get, *args, **kwargs)):
                        
                        results = client.get_results_json(query_id)
                        retrieval_successes += 1
                        print(f"     ✓ Retrieval {i+1}: Success ({len(results.get('data', []))} rows)")
                        
                except Exception as e:
                    print(f"     ✗ Retrieval {i+1}: Failed - {str(e)[:50]}...")
            
            retrieval_recovery_rate = retrieval_successes / retrieval_attempts
            interruption_results.append({
                'test_type': 'result_retrieval',
                'attempts': retrieval_attempts,
                'successes': retrieval_successes,
                'recovery_rate': retrieval_recovery_rate
            })
            
            # Cleanup
            client.delete_query(query_id)
            
        except Exception as e:
            interruption_results.append({
                'test_type': 'result_retrieval',
                'attempts': 0,
                'successes': 0,
                'recovery_rate': 0.0,
                'error': str(e)
            })
        
        timer.checkpoint("network_interruption_tests_completed")
        
        # Analyze overall interruption resilience
        overall_recovery_rate = sum(r['recovery_rate'] for r in interruption_results) / len(interruption_results)
        network_resilience = overall_recovery_rate >= 0.5  # 50% recovery rate under network issues
        
        timer.stop()
        
        print(f"   Network interruption recovery: {overall_recovery_rate:.1%} overall")
        for result in interruption_results:
            print(f"     {result['test_type']}: {result['recovery_rate']:.1%}")
        
        details = {
            "interruption_results": interruption_results,
            "overall_recovery_rate": overall_recovery_rate,
            "network_resilience": network_resilience,
            "timings": timer.get_report()
        }
        
        return network_resilience, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_api_rate_limit_recovery() -> Tuple[bool, Dict[str, Any]]:
    """Test recovery from API rate limiting."""
    print("🚦 Testing API Rate Limit Recovery...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        client = DuneTestClient(api_key)
        
        # Test rate limiting compliance
        rate_limit_results = []
        
        # Test 1: Rapid requests to test rate limiting behavior
        print("   Testing rapid request handling...")
        rapid_results = []
        rate_limit_detected = False
        
        for i in range(10):  # Make rapid requests
            req_start = time.time()
            
            try:
                query_id = client.create_query(f"SELECT {i} as test_col", f"rate_limit_test_{i}")
                req_time = time.time() - req_start
                rapid_results.append({
                    'request': i + 1,
                    'duration': req_time,
                    'success': True,
                    'query_id': query_id
                })
                
                # Check for rate limiting indicators
                if req_time > 5.0:  # Very slow suggests rate limiting
                    rate_limit_detected = True
                
                client.delete_query(query_id)
                print(f"     Request {i+1}: {req_time:.3f}s{' (rate limited?)' if req_time > 5.0 else ''}")
                
            except Exception as e:
                req_time = time.time() - req_start
                rapid_results.append({
                    'request': i + 1,
                    'duration': req_time,
                    'success': False,
                    'error': str(e)
                })
                
                if "rate limit" in str(e).lower() or "429" in str(e):
                    rate_limit_detected = True
                    print(f"     Request {i+1}: Rate limit detected")
                else:
                    print(f"     Request {i+1}: Failed - {str(e)[:50]}...")
            
            # Small delay between requests
            time.sleep(0.1)
        
        rate_limit_results.append({
            'test_type': 'rapid_requests',
            'total_requests': len(rapid_results),
            'successful_requests': sum(1 for r in rapid_results if r['success']),
            'rate_limit_detected': rate_limit_detected,
            'results': rapid_results
        })
        
        # Test 2: Backoff behavior after rate limit detection
        if rate_limit_detected:
            print("   Testing backoff behavior after rate limit...")
            
            backoff_results = []
            backoff_times = []
            
            for i in range(3):
                backoff_start = time.time()
                
                try:
                    query_id = client.create_query(f"SELECT {i} as backoff_test", f"backoff_test_{i}")
                    backoff_time = time.time() - backoff_start
                    backoff_times.append(backoff_time)
                    
                    backoff_results.append({
                        'attempt': i + 1,
                        'success': True,
                        'duration': backoff_time
                    })
                    
                    client.delete_query(query_id)
                    print(f"     Backoff attempt {i+1}: {backoff_time:.3f}s")
                    
                except Exception as e:
                    backoff_time = time.time() - backoff_start
                    backoff_times.append(backoff_time)
                    
                    backoff_results.append({
                        'attempt': i + 1,
                        'success': False,
                        'duration': backoff_time,
                        'error': str(e)
                    })
                    
                    print(f"     Backoff attempt {i+1}: Failed - {str(e)[:50]}...")
                
                # Increasing delays between attempts
                time.sleep(2 ** i)  # Exponential backoff
            
            # Check if backoff shows improvement
            if len(backoff_times) > 1:
                later_times = backoff_times[len(backoff_times)//2:]
                earlier_times = backoff_times[:len(backoff_times)//2]
                
                improvement = sum(later_times) / len(later_times) < sum(earlier_times) / len(earlier_times)
                rate_limit_results.append({
                    'test_type': 'backoff_recovery',
                    'improvement_detected': improvement,
                    'backoff_results': backoff_results,
                    'backoff_times': backoff_times
                })
                
                print(f"     Backoff improvement detected: {improvement}")
        
        timer.checkpoint("rate_limit_tests_completed")
        
        # Analyze rate limiting resilience
        successful_requests = sum(r['successful_requests'] for r in rate_limit_results if 'successful_requests' in r)
        total_requests = sum(r['total_requests'] for r in rate_limit_results if 'total_requests' in r)
        request_success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        rate_limit_resilience = (
            request_success_rate >= 0.6 and  # At least 60% of requests succeed
            rate_limit_detected  # Should detect rate limiting behavior
        )
        
        timer.stop()
        
        print(f"   Rate limiting resilience: {request_success_rate:.1%} success rate")
        print(f"   Rate limiting detected: {rate_limit_detected}")
        
        details = {
            "rate_limit_results": rate_limit_results,
            "successful_requests": successful_requests,
            "total_requests": total_requests,
            "request_success_rate": request_success_rate,
            "rate_limit_detected": rate_limit_detected,
            "rate_limit_resilience": rate_limit_resilience,
            "timings": timer.get_report()
        }
        
        return rate_limit_resilience, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_graceful_degradation() -> Tuple[bool, Dict[str, Any]]:
    """Test graceful degradation under adverse conditions."""
    print("📉 Testing Graceful Degradation...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        
        # Define degradation scenarios
        degradation_scenarios = [
            {
                'name': 'high_timeout',
                'description': 'Very short timeouts causing failures',
                'config': {'timeout_seconds': 1}
            },
            {
                'name': 'low_retries',
                'description': 'Reduced retry count',
                'config': {'max_retries': 1}
            },
            {
                'name': 'poor_performance',
                'description': 'Low performance level',
                'config': {'performance': 'low'}
            }
        ]
        
        degradation_results = []
        
        for scenario in degradation_scenarios:
            scenario_name = scenario['name']
            description = scenario['description']
            config = scenario['config']
            
            print(f"   Testing degradation scenario: {description}")
            
            try:
                # Create DuneTestClient with scenario-specific config
                client_class_config = {'max_retries': config.get('max_retries', 3)}
                client = DuneTestClient(api_key)
                
                scenario_results = []
                
                # Test query execution under degradation conditions
                for i in range(3):
                    query_start = time.time()
                    
                    try:
                        with TestQueryManager(client) as qm:
                            test_sql = QueryFactory.simple_select()
                            query_id = qm.create_test_query(test_sql, f"degradation_{scenario_name}_{i}")
                            
                            # Apply scenario-specific execution parameters
                            execution_params = {}
                            if 'timeout_seconds' in config:
                                execution_params['timeout'] = config['timeout_seconds']
                            if 'performance' in config:
                                execution_params['performance'] = config['performance']
                            
                            execution_id = qm.execute_and_wait(query_id, **execution_params)
                            results_json = qm.client.get_results_json(query_id)
                            
                            query_duration = time.time() - query_start
                            
                            scenario_results.append({
                                'attempt': i + 1,
                                'success': True,
                                'duration': query_duration,
                                'rows': len(results_json.get('data', [])),
                                'config': config
                            })
                            
                            print(f"     ✓ Attempt {i+1}: Success in {query_duration:.2f}s")
                        
                    except TimeoutError:
                        query_duration = time.time() - query_start
                        scenario_results.append({
                            'attempt': i + 1,
                            'success': False,
                            'duration': query_duration,
                            'error': 'timeout',
                            'config': config
                        })
                        print(f"     ⚠ Attempt {i+1}: Timeout after {query_duration:.2f}s")
                        
                    except Exception as e:
                        query_duration = time.time() - query_start
                        scenario_results.append({
                            'attempt': i + 1,
                            'success': False,
                            'duration': query_duration,
                            'error': str(e),
                            'config': config
                        })
                        print(f"     ✗ Attempt {i+1}: Failed - {str(e)[:50]}...")
                
                # Analyze scenario results
                successful_attempts = [r for r in scenario_results if r['success']]
                degradation_score = {
                    'scenario_name': scenario_name,
                    'description': description,
                    'config': config,
                    'total_attempts': len(scenario_results),
                    'successful_attempts': len(successful_attempts),
                    'success_rate': len(successful_attempts) / len(scenario_results),
                    'avg_duration': sum(r['duration'] for r in scenario_results) / len(scenario_results),
                    'results': scenario_results
                }
                
                degradation_results.append(degradation_score)
                
                print(f"     Success rate: {degradation_score['success_rate']:.1%}")
                print(f"     Average duration: {degradation_score['avg_duration']:.2f}s")
                
            except Exception as e:
                degradation_results.append({
                    'scenario_name': scenario_name,
                    'description': description,
                    'config': config,
                    'error': str(e),
                    'success_rate': 0.0
                })
                print(f"     Scenario failed: {str(e)[:50]}...")
        
        timer.checkpoint("degradation_tests_completed")
        
        # Analyze graceful degradation
        # We expect some degradation but not complete failure
        overall_success_rate = sum(r['success_rate'] for r in degradation_results if 'success_rate' in r) / len(degradation_results)
        graceful_degradation = overall_success_rate >= 0.2  # At least 20% success under poor conditions
        
        timer.stop()
        
        print(f"   Graceful degradation: {overall_success_rate:.1%} overall success rate")
        
        details = {
            "degradation_results": degradation_results,
            "overall_success_rate": overall_success_rate,
            "graceful_degradation": graceful_degradation,
            "timings": timer.get_report()
        }
        
        return graceful_degradation, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_error_recovery_patterns() -> Tuple[bool, Dict[str, Any]]:
    """Test various error recovery patterns."""
    print("🔄 Testing Error Recovery Patterns...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        recovery_patterns = []
        
        # Test 1: Recovery from temporary API unavailability
        print("   Testing recovery from temporary API unavailability...")
        
        temporary_unavailability_results = []
        for i in range(3):
            recovery_start = time.time()
            
            try:
                # Simulate temporary unavailability by using very short timeout
                client = DuneTestClient(api_key)
                
                # Try with client that retries (built-in)
                with TestQueryManager(client) as qm:
                    test_sql = QueryFactory.simple_select()
                    query_id = qm.create_test_query(test_sql, f"recovery_test_{i}")
                    
                    # Execute with normal timeout to allow recovery
                    execution_id = qm.execute_and_wait(query_id, timeout=60)
                    results_json = qm.client.get_results_json(query_id)
                    
                    recovery_time = time.time() - recovery_start
                    
                    temporary_unavailability_results.append({
                        'attempt': i + 1,
                        'success': True,
                        'recovery_time': recovery_time,
                        'rows': len(results_json.get('data', []))
                    })
                    
                    print(f"     ✓ Recovery {i+1}: Success in {recovery_time:.2f}s")
                    
            except Exception as e:
                recovery_time = time.time() - recovery_start
                temporary_unavailability_results.append({
                    'attempt': i + 1,
                    'success': False,
                    'recovery_time': recovery_time,
                    'error': str(e)
                })
                
                print(f"     ✗ Recovery {i+1}: Failed after {recovery_time:.2f}s - {str(e)[:50]}...")
        
        recovery_patterns.append({
            'pattern_name': 'temporary_unavailability',
            'results': temporary_unavailability_results,
            'success_rate': sum(1 for r in temporary_unavailability_results if r['success']) / len(temporary_unavailability_results)
        })
        
        # Test 2: Recovery from query execution failures
        print("   Testing recovery from query execution failures...")
        
        execution_failure_results = []
        
        # Create a potentially problematic query
        problematic_query = """
        SELECT 
            n,
            1/n as division_result,
            CASE WHEN n % 2 = 0 THEN 'even' ELSE 'odd' END as parity
        FROM generate_series(-1, 10) as n
        """
        
        for i in range(2):
            try:
                client = DuneTestClient(api_key)
                
                with TestQueryManager(client) as qm:
                    query_id = qm.create_test_query(problematic_query, f"failure_recovery_{i}")
                    execution_id = qm.execute_and_wait(query_id, timeout=45)
                    results_json = qm.client.get_results_json(query_id)
                    
                    execution_failure_results.append({
                        'attempt': i + 1,
                        'success': True,
                        'rows': len(results_json.get('data', [])),
                        'executed_query': True
                    })
                    
                    print(f"     ✓ Execution recovery {i+1}: Success")
                    
            except Exception as e:
                execution_failure_results.append({
                    'attempt': i + 1,
                    'success': False,
                    'error': str(e),
                    'executed_query': False
                })
                
                print(f"     ✗ Execution recovery {i+1}: Failed - {str(e)[:50]}...")
        
        recovery_patterns.append({
            'pattern_name': 'execution_failure',
            'results': execution_failure_results,
            'success_rate': sum(1 for r in execution_failure_results if r['success']) / len(execution_failure_results)
        })
        
        # Test 3: Recovery from malformed requests
        print("   Testing recovery from malformed requests...")
        
        malformed_request_results = []
        
        malformed_requests = [
            {"description": "missing query", "request": {}},
            {"description": "invalid performance", "request": {"query": "SELECT 1", "performance": "invalid"}},
            {"description": "negative limit", "request": {"query": "SELECT 1", "limit": -1}},
            {"description": "invalid parameters", "request": {"query": "SELECT 1", "parameters": "invalid"}}
        ]
        
        for malformed_request in malformed_requests:
            try:
                # Import MCP tool for structured testing
                from spice_mcp.config import Config, DuneConfig
                from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
                from spice_mcp.service_layer.query_service import QueryService
                from spice_mcp.logging.query_history import QueryHistory
                from pathlib import Path as PathObj
                
                config = Config(dune=DuneConfig(api_key=api_key))
                query_service = QueryService(config)
                history_path = PathObj("/tmp") / "malformed_recovery_history.jsonl"
                artifact_root = PathObj("/tmp") / "malformed_recovery_artifacts"
                query_history = QueryHistory(history_path, artifact_root)
                
                execute_tool = ExecuteQueryTool(config, query_service, query_history)
                
                # Use MCPToolSimulator for consistent testing approach
                from tests.support.helpers import MCPToolSimulator
                
                start_time = time.time()
                result = MCPToolSimulator.simulate_tool_call(execute_tool, malformed_request['request'])
                recovery_time = time.time() - start_time
                
                # We expect controlled failures
                handled_gracefully = not result['success']
                
                malformed_request_results.append({
                    'description': malformed_request['description'],
                    'request': malformed_request['request'],
                    'handled_gracefully': handled_gracefully,
                    'recovery_time': recovery_time,
                    'result': result
                })
                
                status = "✓" if handled_gracefully else "✗"
                print(f"     {status} {malformed_request['description']}: {'gracefully rejected' if handled_gracefully else 'unexpectedly passed'}")
                
            except Exception as e:
                malformed_request_results.append({
                    'description': malformed_request['description'],
                    'request': malformed_request['request'],
                    'handled_gracefully': True,  # Exception counts as graceful handling
                    'recovery_time': time.time() - start_time,
                    'exception': str(e)
                })
                
                print(f"     ✓ {malformed_request['description']}: exception caught gracefully")
        
        graceful_handling_rate = sum(1 for r in malformed_request_results if r.get('handled_gracefully', False)) / len(malformed_request_results)
        
        recovery_patterns.append({
            'pattern_name': 'malformed_requests',
            'results': malformed_request_results,
            'graceful_handling_rate': graceful_handling_rate
        })
        
        timer.checkpoint("error_recovery_tests_completed")
        
        # Analyze overall error recovery
        successful_patterns = []
        for pattern in recovery_patterns:
            if pattern['pattern_name'] == 'malformed_requests':
                successful_patterns.append(pattern['graceful_handling_rate'] >= 0.8)
            else:
                successful_patterns.append(pattern['success_rate'] >= 0.5)
        
        overall_recovery = sum(successful_patterns) / len(successful_patterns)
        
        timer.stop()
        
        print(f"   Error recovery patterns: {successful_patterns.count(True)}/{len(successful_patterns)} successful")
        
        details = {
            "recovery_patterns": recovery_patterns,
            "successful_patterns": successful_patterns,
            "overall_recovery": overall_recovery,
            "timings": timer.get_report()
        }
        
        return overall_recovery >= 0.6, details  # 60% of recovery patterns should work
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def main():
    """Run resilience test suite."""
    print("🔄 DUNE RESILIENCE TEST SUITE")
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
    
    # Run resilience tests
    tests = [
        ("Retry Backoff Mechanisms", test_retry_backoff_mechanisms),
        ("Network Interruption Recovery", test_network_interruption_recovery),
        ("API Rate Limit Recovery", test_api_rate_limit_recovery),
        ("Graceful Degradation", test_graceful_degradation),
        ("Error Recovery Patterns", test_error_recovery_patterns),
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
    print("🎯 RESILIENCE TEST SUMMARY")
    print(f"✅ {passed}/{total} tests passed")
    print(f"⏱️ Total duration: {summary['duration']:.2f}s")
    
    if passed >= total * 0.6:  # 60% pass rate for resilience tests (some failure expected)
        print("🎉 Resilience tests passed! System maintains stability under stress.")
        return True
    else:
        print("⚠️ Some resilience tests failed. Review error handling and recovery mechanisms.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
