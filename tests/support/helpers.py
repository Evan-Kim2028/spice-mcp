"""
Common test patterns and utilities.
"""
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestEnvironment:
    """Manages test environment setup and cleanup."""
    
    def __init__(self):
        self.temp_dirs: List[Path] = []
        self.created_files: List[Path] = []
        self.env_vars: Dict[str, str] = {}
    
    @contextmanager
    def temp_directory(self):
        """Create a temporary directory and auto-cleanup."""
        temp_dir = Path(tempfile.mkdtemp(prefix="spice_test_"))
        self.temp_dirs.append(temp_dir)
        try:
            yield temp_dir
        finally:
            self._cleanup_temp_dir(temp_dir)
    
    def _cleanup_temp_dir(self, temp_dir: Path):
        """Clean up a temporary directory."""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                self.temp_dirs.remove(temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup {temp_dir}: {e}")
    
    def create_env_file(self, api_key: str, extra_vars: Dict[str, str] = None) -> Path:
        """Create a temporary .env file for testing."""
        with self.temp_directory() as temp_dir:
            env_file = temp_dir / ".env"
            content = f"DUNE_API_KEY={api_key}\n"
            
            if extra_vars:
                for key, value in extra_vars.items():
                    content += f"{key}={value}\n"
            
            env_file.write_text(content)
            self.created_files.append(env_file)
            return env_file
    
    def set_env_var(self, key: str, value: str):
        """Set environment variable for test."""
        original_value = os.environ.get(key)
        os.environ[key] = value
        self.env_vars[key] = original_value or "UNSET"
    
    def cleanup_env_vars(self):
        """Restore environment variables."""
        for key, original_value in self.env_vars.items():
            if original_value == "UNSET":
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        self.env_vars.clear()
    
    def cleanup_all(self):
        """Clean up all resources."""
        # Clean up temp directories
        for temp_dir in self.temp_dirs[:]:
            self._cleanup_temp_dir(temp_dir)
        
        # Clean up created files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete {file_path}: {e}")
        self.created_files.clear()
        
        # Restore environment
        self.cleanup_env_vars()


class PerformanceTimer:
    """Performance measurement utility."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.checkpoints = {}
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
        self.checkpoints = {}
    
    def checkpoint(self, name: str):
        """Record a checkpoint time."""
        if self.start_time is not None:
            self.checkpoints[name] = time.time() - self.start_time
    
    def stop(self):
        """Stop timing."""
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """Get total duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_checkpoint(self, name: str) -> Optional[float]:
        """Get checkpoint time."""
        return self.checkpoints.get(name)
    
    def get_report(self) -> Dict[str, Any]:
        """Get performance report."""
        report = {
            'total_duration': self.duration,
            'checkpoints': self.checkpoints.copy()
        }
        return report


class RetryMechanism:
    """Generic retry mechanism with backoff."""
    
    @staticmethod
    def retry_with_backoff(func, max_retries: int = 3, backoff_factor: float = 1.0,
                          exceptions: Tuple = (Exception,), default_return: Any = None):
        """Retry function with exponential backoff."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = backoff_factor * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                break
        
        return default_return


class TestResultCollector:
    """Collect and aggregate test results."""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def start_collection(self):
        """Start result collection."""
        self.start_time = time.time()
        self.results = []
    
    def add_result(self, test_name: str, success: bool, details: Dict[str, Any] = None,
                   error: str = None):
        """Add a test result."""
        result = {
            'test_name': test_name,
            'success': success,
            'timestamp': time.time(),
            'details': details or {},
            'error': error
        }
        self.results.append(result)
    
    def finish_collection(self):
        """Finish result collection."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get collection summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        duration = (self.end_time or time.time()) - (self.start_time or time.time())
        
        return {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'duration': duration,
            'failed_tests': [r for r in self.results if not r['success']],
            'passed_tests': [r for r in self.results if r['success']]
        }
    
    def export_to_file(self, output_path: Path):
        """Export results to file."""
        import json
        summary = self.get_summary()
        
        report = {
            'summary': summary,
            'all_results': self.results,
            'metadata': {
                'start_time': self.start_time,
                'end_time': self.end_time,
                'total_duration': summary['duration']
            }
        }
        
        output_path.write_text(json.dumps(report, indent=2, default=str))


class MCPToolSimulator:
    """Simulate MCP tool interactions."""
    
    @staticmethod
    def simulate_tool_call(tool_instance, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate an MCP tool call and normalize the response."""
        try:
            if hasattr(tool_instance, 'execute'):
                if hasattr(tool_instance.execute, '__call__'):
                    # Async function
                    import asyncio
                    result = asyncio.run(tool_instance.execute(**parameters))
                else:
                    # Regular function
                    result = tool_instance.execute(**parameters)
            else:
                raise ValueError("Tool instance doesn't have execute method")
            
            # Normalize response to MCP format
            if isinstance(result, dict):
                return {
                    'success': True,
                    'data': result,
                    'type': 'dict'
                }
            elif hasattr(result, 'to_dict'):
                return {
                    'success': True,
                    'data': result.to_dict(),
                    'type': 'dataframe'
                }
            else:
                return {
                    'success': True,
                    'data': str(result),
                    'type': 'string'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    @staticmethod
    def validate_tool_schema(tool_instance) -> Dict[str, Any]:
        """Validate tool schema and parameter requirements."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if not hasattr(tool_instance, 'get_parameter_schema'):
                validation['valid'] = False
                validation['errors'].append("Tool doesn't have get_parameter_schema method")
                return validation
            
            schema = tool_instance.get_parameter_schema()
            
            if not isinstance(schema, dict):
                validation['valid'] = False
                validation['errors'].append("Schema is not a dictionary")
                return validation
            
            # Check required schema components
            if 'type' not in schema:
                validation['warnings'].append("Schema missing 'type' field")
            
            if 'properties' not in schema:
                validation['warnings'].append("Schema missing 'properties' field")
            elif not isinstance(schema['properties'], dict):
                validation['valid'] = False
                validation['errors'].append("Schema 'properties' is not a dictionary")
            
            return validation
            
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Schema validation exception: {e}")
            return validation


def run_external_command(cmd: List[str], cwd: Optional[Path] = None,
                        timeout: int = 120) -> Dict[str, Any]:
    """Run an external command and capture output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timed out',
            'timeout': timeout
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result
