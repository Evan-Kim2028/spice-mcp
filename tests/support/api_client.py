"""
Enhanced API client wrapper for testing with retry logic and better error handling.
"""
import os
import time
import json
from typing import Dict, Any, Optional, Tuple
import requests
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from spice_mcp.adapters.dune import urls, transport


class DuneTestClient:
    """Enhanced client wrapper for Dune API testing with retry logic."""
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3):
        self.api_key = api_key or os.getenv("DUNE_API_KEY")
        if not self.api_key:
            raise ValueError("DUNE_API_KEY must be provided")
        
        self.max_retries = max_retries
        self.base_url = urls._base_url()
        self.headers = urls.get_headers(api_key=self.api_key)
    
    def create_query(self, sql: str, name: str = None, is_private: bool = True) -> int:
        """Create a Dune query with retry logic."""
        if name is None:
            name = f"test_query_{int(time.time())}"
        
        url = urls.url_templates['query_create']
        payload = {
            "query_sql": sql,
            "name": name,
            "dataset": "preview",
            "is_private": is_private
        }
        
        return self._retryRequest(
            requests.post, url, json=payload,
            error_context=f"create query with name: {name}"
        ).json()['query_id']
    
    def execute_query(self, query_id: int, parameters: Dict[str, Any] = None, 
                     performance: str = "medium") -> str:
        """Execute a query and return execution ID."""
        url = urls.get_query_execute_url(query_id)
        payload = {
            "performance": performance,
            "query_parameters": parameters or {}
        }
        
        response = self._retryRequest(
            requests.post, url, json=payload,
            error_context=f"execute query {query_id}"
        )
        return response.json()['execution_id']
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status with retry logic."""
        url = urls.url_templates['execution_status'].format(execution_id=execution_id)
        return self._retryRequest(
            requests.get, url, 
            error_context=f"get execution status {execution_id}"
        ).json()
    
    def get_results_csv(self, execution_id: str) -> str:
        """Get query results as CSV with retry logic."""
        url = urls.url_templates['execution_results'].format(execution_id=execution_id)
        response = self._retryRequest(
            requests.get, url,
            error_context=f"get results CSV {execution_id}"
        )
        return response.text
    
    def get_results_json(self, execution_id: str) -> Dict[str, Any]:
        """Get query results as JSON with retry logic."""
        url = urls.url_templates['query_results_json'].format(query_id=execution_id)
        return self._retryRequest(
            requests.get, url,
            error_context=f"get results JSON {execution_id}"
        ).json()
    
    def wait_for_completion(self, execution_id: str, timeout: int = 120, 
                           poll_interval: float = 1.0) -> Dict[str, Any]:
        """Wait for query execution to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_execution_status(execution_id)
            state = status.get('state', '')
            
            if state == 'QUERY_STATE_COMPLETED':
                return status
            elif state in ['QUERY_STATE_FAILED', 'QUERY_STATE_CANCELLED']:
                raise Exception(f"Query execution failed: {status.get('error', 'Unknown error')}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Query execution timed out after {timeout} seconds")
    
    def delete_query(self, query_id: int) -> bool:
        """Delete a query (cleanup)."""
        try:
            url = urls.url_templates['query'].format(query_id=query_id)
            requests.delete(url, headers=self.headers, timeout=10.0)
            return True
        except:
            return False  # Best effort cleanup
    
    def _retryRequest(self, method, url: str, max_retries: Optional[int] = None, 
                     error_context: str = "", **kwargs) -> requests.Response:
        """Execute HTTP request with retry logic."""
        max_retries = max_retries or self.max_retries
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Add timeout if not provided
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = 30.0
                
                response = method(url, headers=self.headers, **kwargs)
                
                # Check for rate limiting
                if response.status_code == 429:
                    if attempt < max_retries:
                        retry_after = int(response.headers.get('Retry-After', 2))
                        print(f"Rate limited, waiting {retry_after}s before retry {attempt + 1}")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise Exception("Rate limit exceeded after all retries")
                
                # Check for other API errors
                if response.status_code >= 400:
                    error_info = ""
                    try:
                        error_data = response.json()
                        error_info = error_data.get('error', response.text)
                    except:
                        error_info = response.text
                    
                    if response.status_code in [500, 502, 503, 504] and attempt < max_retries:
                        wait_time = (2 ** attempt) + 1  # Exponential backoff
                        print(f"Server error {response.status_code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    
                    raise Exception(f"API error {response.status_code}: {error_info}")
                
                return response
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 1
                    print(f"Timeout, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise TimeoutError(f"Request timeout after {max_retries} retries for {error_context}")
            
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 1
                    print(f"Connection error, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise ConnectionError(f"Connection failed after {max_retries} retries for {error_context}")
            
            except Exception as e:
                last_exception = e
                if "rate limit" not in str(e).lower() and attempt < max_retries:
                    wait_time = (2 ** attempt) + 1
                    print(f"Error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                raise
        
        # If we get here, all retries failed
        raise Exception(f"All retries failed for {error_context}. Last error: {last_exception}")


class TestQueryManager:
    """Manages lifecycle of test queries with automatic cleanup."""
    
    def __init__(self, client: DuneTestClient):
        self.client = client
        self.created_queries: Dict[int, Dict[str, Any]] = {}
    
    def create_test_query(self, sql: str, name: str = None, **kwargs) -> int:
        """Create a test query and register it for cleanup."""
        query_id = self.client.create_query(sql, name, **kwargs)
        self.created_queries[query_id] = {
            'name': name,
            'sql': sql,
            'created_at': time.time()
        }
        return query_id
    
    def execute_and_wait(self, query_id: int, parameters: Dict[str, Any] = None, 
                        performance: str = "medium", **kwargs) -> str:
        """Execute query and wait for completion."""
        execution_id = self.client.execute_query(query_id, parameters, performance)
        status = self.client.wait_for_completion(execution_id, **kwargs)
        return execution_id
    
    def cleanup_all(self):
        """Clean up all created test queries."""
        for query_id in list(self.created_queries.keys()):
            try:
                self.client.delete_query(query_id)
                del self.created_queries[query_id]
                print(f"Cleaned up query {query_id}")
            except Exception as e:
                print(f"Failed to cleanup query {query_id}: {e}")
    
    def get_query_info(self, query_id: int) -> Dict[str, Any]:
        """Get information about a created query."""
        return self.created_queries.get(query_id, {})
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()
