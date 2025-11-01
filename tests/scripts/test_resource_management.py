#!/usr/bin/env python3
"""
Resource Management Test - Tier 4 Test Suite

Tests file descriptor limits, memory management, cleanup reliability, and resource leak detection.
Ensures the system properly manages resources and doesn't accumulate leaks over time.
"""
import os
import sys
import time
import json
import gc
import psutil
import threading
import tempfile
import weakref
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tests.support.api_client import DuneTestClient, TestQueryManager
from tests.support.helpers import PerformanceTimer, TestResultCollector, TestEnvironment
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

def get_process_resource_info() -> Dict[str, Any]:
    """Get comprehensive process resource information."""
    process = psutil.Process()
    
    # Basic resource info
    memory_info = process.memory_info()
    cpu_percent = process.cpu_percent()
    
    # File descriptors (Unix systems)
    try:
        file_descriptors = process.num_fds()
    except (AttributeError, OSError):
        file_descriptors = 0  # Not available on Windows
    
    # Thread count
    thread_count = process.num_threads()
    
    # Memory details
    memory_full_info = {
        'rss': memory_info.rss,
        'vms': memory_info.vms,
        'shared': getattr(memory_info, 'shared', 0),
        'text': getattr(memory_info, 'text', 0),
        'lib': getattr(memory_info, 'lib', 0),
        'data': getattr(memory_info, 'data', 0),
    }
    
    # Open files (if available)
    try:
        open_files = len(process.open_files())
    except (AttributeError, psutil.AccessDenied):
        open_files = 0
    
    return {
        'pid': process.pid,
        'memory_mb': memory_info.rss / 1024 / 1024,
        'cpu_percent': cpu_percent,
        'file_descriptors': file_descriptors,
        'open_files': open_files,
        'thread_count': thread_count,
        'memory_info': memory_full_info,
        'timestamp': time.time()
    }

def test_memory_leak_detection() -> Tuple[bool, Dict[str, Any]]:
    """Test for memory leaks over time."""
    print("🔍 Testing Memory Leak Detection...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        
        # Track memory through operations
        memory_snapshots = []
        
        # Create weak references to track object cleanup
        created_objects = []
        
        # Test multiple cycles to detect leaks
        for cycle in range(5):
            print(f"   Memory leak test cycle {cycle + 1}/5")
            
            cycle_start_memory = get_process_resource_info()
            
            # Create resource-intensive objects
            cycle_objects = []
            
            for i in range(10):
                try:
                    with TestQueryManager(DuneTestClient(api_key)) as qm:
                        test_sql = QueryFactory.data_types_query()
                        query_id = qm.create_test_query(test_sql, f"leak_test_{cycle}_{i}")
                        
                        execution_id = qm.execute_and_wait(query_id, timeout=60)
                        results_json = qm.client.get_results_json(query_id)
                        
                        # Store weak references to objects
                        cycle_objects.extend([weakref.ref(qm), weakref.ref(query_id)])
                        
                    except Exception as e:
                        print(f"     Cycle {cycle+1}, Query {i+1} failed: {str(e)[:50]}...")
                
            cycle_end_memory = get_process_resource_info()
            
            # Force garbage collection
            gc.collect()
            time.sleep(1)
            
            post_gc_memory = get_process_resource_info()
            
            memory_snapshots.append({
                'cycle': cycle + 1,
                'start_memory_mb': cycle_start_memory['memory_mb'],
                'end_memory_mb': cycle_end_memory['memory_mb'],
                'post_gc_memory_mb': post_gc_memory['memory_mb'],
                'memory_growth': post_gc_memory['memory_mb'] - memory_snapshots[0]['start_memory_mb'] if memory_snapshots else 0,
                'objects_tracked': len(cycle_objects)
            })
            
            print(f"     Memory growth: {memory_snapshots[-1]['memory_growth']:.1f} MB")
        
        timer.checkpoint("memory_leak_tests_completed")
        
        # Analyze memory trend
        if len(memory_snapshots) > 1:
            memory_values = [s['post_gc_memory_mb'] for s in memory_snapshots]
            initial_memory = memory_values[0]
            final_memory = memory_values[-1]
            total_growth = final_memory - initial_memory
            
            # Check if growth is linear (leak) or stable (no leak)
            if len(memory_values) > 2:
                # Simple linear trend detection
                x_values = list(range(len(memory_values)))
                avg_x = sum(x_values) / len(x_values)
                avg_y = sum(memory_values) / len(memory_values)
                
                num = sum((x - avg_x) * (y - avg_y) for x, y in zip(x_values, memory_values))
                den = sum((x - avg_x) ** 2 for x in x_values)
                
                slope = num / den if den != 0 else 0
            else:
                slope = 0
            
            memory_leak_ok = (
                total_growth < 100 and  # Less than 100MB total growth
                abs(slope) < 1.0  # Less than 1MB per cycle slope
            )
        else:
            memory_leak_ok = False
            slope = 0
            total_growth = 0
        
        timer.stop()
        
        print(f"   Total memory growth: {total_growth:.1f} MB")
        print(f"   Memory slope: {slope:.3f} MB/cycle")
        
        details = {
            "memory_snapshots": memory_snapshots,
            "total_growth_mb": total_growth,
            "slope": slope,
            "memory_leak_ok": memory_leak_ok,
            "timings": timer.get_report()
        }
        
        return memory_leak_ok, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def test_file_descriptor_cleanup() -> Tuple[bool, Dict[str, Any]]:
    """Test file descriptor cleanup and limits."""
    print("📁 Testing File Descriptor Cleanup...")
    timer = PerformanceTimer()
    
    try:
        timer.start()
        
        api_key = os.getenv("DUNE_API_KEY")
        
        # Track file descriptors through operations
        fd_snapshots = []
        
        # Get initial state
        initial_resources = get_process_resource_info()
        initial_fds = initial_resources['file_descriptors']
        print(f"   Initial file descriptors: {initial_fds}")
        
        # Run multiple concurrent operations
        for cycle in range(3):
            print(f"   FD test cycle {cycle + 1}/3")
            
            cycle_start_fds = get_process_resource_info()['file_descriptors']
            peak_fds = cycle_start_fds
            
            # Use thread pool for concurrent operations
            def concurrent_query_operation(thread_id):
                try:
                    with TestQueryManager(DuneTestClient(api_key)) as qm:
                        test_sql = QueryFactory.simple_select()
                        query_id = qm.create_test_query(test_sql, f"fd_test_{cycle}_{thread_id}")
                        
                        execution_id = qm.execute_and_wait(query_id, timeout=45)
                        results_json = qm.client.get_results_json(query_id)
                        
                        return {
                            'thread_id': thread_id,
                            'success': True,
                            'rows': len(results_json.get('data', []))
                        }
                        
                except Exception as e:
                    return {
                        'thread_id': thread_id,
                        'success': False,
                        'error': str(e)
                    }
            
            # Run 3 concurrent operations
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(concurrent_query_operation, i) for i in range(3)]
                results = []
                
                for future in as_completed(futures):
                    result = future.result(timeout=120)
                    results.append(result)
                    
                    # Check FD usage during execution
                    current_fds = get_process_resource_info()['file_descriptors']
                    peak_fds = max(peak_fds, current_fds)
                    
                    status = "✓" if result['success'] else "✗"
                    print(f"     {status} Thread {result['thread_id']}: {current_fds} FDs")
            
            # Wait for cleanup
            time.sleep(2)
            
            cycle_end_fds = get_process_resource_info()['file_descriptors']
            
            fd_snapshots.append({
                'cycle': cycle + 1,
                'start_fds': cycle_start_fds,
                'peak_fds': peak_fds,
                'end_fds': cycle_end_fds,
                'fd_increase': peak_fds - cycle_start_fds,
                'fd_cleanup': peak_fds - cycle_end_fds,
                'cleanup_efficiency': (peak_fds - cycle_end_fds) / max(peak_fds - cycle_start_fds, 1),
                'successful_operations': sum(1 for r in results if r['success'])
            })
            
            print(f"     FD cleanup: {fd_snapshots[-1]['fd_cleanup']} ({fd_snapshots[-1]['cleanup_efficiency']:.1%})")
        
        # Check final state
        final_resources = get_process_resource_info()
        final_fds = final_resources['file_descriptors']
        
        timer.checkpoint("fd_cleanup_tests_completed")
        
        timer.stop()
        
        # Analyze FD management
        total_fd_cleanup = sum(s['fd_cleanup'] for s in fd_snapshots)
        avg_cleanup_efficiency = sum(s['cleanup_efficiency'] for s in fd_snapshots) / len(fd_snapshots)
        total_operations = sum(s['successful_operations'] for s in fd_snapshots)
        
        fd_management_ok = (
            avg_cleanup_efficiency > 0.7 and  # 70% cleanup efficiency
            total_operations >= 7 and  # At least 7 successful operations out of 9
            (final_fds - initial_fds) < 50  # Less than 50 FDs remaining
        )
        
        print(f"   Total FD cleanup: {total_fd_cleanup}")
        print(f"   Average cleanup efficiency: {avg_cleanup_efficiency:.1%}")
        print(f"   Final FD count: {final_fds} (increase: {final_fds - initial_fds})")
        
        details = {
            "fd_snapshots": fd_snapshots,
            "initial_fds": initial_fds,
            "final_fds": final_fds,
            "total_fd_cleanup": total_fd_cleanup,
            "avg_cleanup_efficiency": avg_cleanup_efficiency,
            "total_operations": total_operations,
            "fd_management_ok": fd_management_ok,
            "timings": timer.get_report()
        }
        
        return fd_management_ok, details
        
    except Exception as e:
        timer.stop()
        return False, {"error": str(e), "timings": timer.get_report()}

def main():
    """Run resource management test suite."""
    print("💾 DUNE RESOURCE MANAGEMENT TEST SUITE")
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
    
    # Run resource management tests
    tests = [
        ("Memory Leak Detection", test_memory_leak_detection),
        ("File Descriptor Cleanup", test_file_descriptor_cleanup),
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
    print("🎯 RESOURCE MANAGEMENT TEST SUMMARY")
    print(f"✅ {passed}/{total} tests passed")
    print(f"⏱️ Total duration: {summary['duration']:.2f}s")
    
    if passed == total:
        print("🎉 Resource management tests passed! No leaks detected.")
        return True
    else:
        print("⚠️ Some resource management tests failed. Review for potential issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
