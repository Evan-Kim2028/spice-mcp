"""
Factory for creating standardized test queries expected to work reliably with Dune API.
"""
from typing import Dict, Tuple, List
import time


class QueryFactory:
    """Factory for creating reliable test queries for Dune API testing."""
    
    @staticmethod
    def simple_select() -> str:
        """Simple deterministic query for basic functionality testing."""
        return "SELECT 1 as test_col, 'fixed_value' as message"
    
    @staticmethod
    def parametric_query() -> Tuple[str, Dict[str, int]]:
        """Query with parameters for testing parameter handling."""
        sql = "SELECT {{limit_count}} as value"
        params = {"limit_count": 5}
        return sql, params
    
    @staticmethod
    def string_parameter_query() -> Tuple[str, Dict[str, str]]:
        """Query with string parameter for testing different parameter types."""
        sql = "SELECT '{{test_string}}' as message, 42 as number"
        params = {"test_string": "hello_world"}
        return sql, params
    
    @staticmethod
    def data_types_query() -> str:
        """Query covering all major Dune data types."""
        return """
        SELECT 
            1 as int_col,
            123.45 as float_col, 
            'test_string' as string_col,
            true as bool_col,
            DOUBLE '123.45' as double_col,
            DATE '2023-01-01' as date_col,
            TIMESTAMP '2023-01-01 12:00:00' as timestamp_col,
            NULL as null_col
        """
    
    @staticmethod
    def joined_query() -> str:
        """More complex query with joins for testing advanced functionality."""
        return """
        SELECT 
            block_time,
            block_number,
            'ethereum_mainnet' as chain
        FROM (
            SELECT 
                DATE '2023-01-01' as block_time,
                1641024000 as block_number
            ) blocks
        WHERE block_time >= DATE '2023-01-01'
        ORDER BY block_time DESC
        LIMIT 5
        """
    
    @staticmethod
    def time_series_query() -> str:
        """Time series query for testing temporal data handling."""
        return """
        SELECT 
            date_trunc('day', block_time) as day,
            COUNT(*) as block_count
        FROM (
            SELECT 
                DATE '2023-01-01' + INTERVAL '1 day' * n as block_time
            FROM (
                SELECT generate_series(0, 4) as n
            ) series
        ) daily_blocks
        GROUP BY day
        ORDER BY day DESC
        LIMIT 7
        """
    
    @staticmethod
    def aggregate_query() -> str:
        """Query with aggregations for testing complex calculations."""
        return """
        SELECT 
            SUM(value) as total_value,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            COUNT(*) as row_count
        FROM (
            SELECT 
                10 as value
            UNION SELECT 20
            UNION SELECT 30
        ) sample_data
        """
    
    @staticmethod
    def stress_test_query(limit: int = 1000) -> str:
        """Query designed to stress test with larger result sets."""
        return f"""
        SELECT 
            n as row_num,
            'row_' || n as row_label,
            n * 1.5 as float_val,
            n % 2 = 0 as is_even
        FROM (
            SELECT generate_series(1, {limit}) as n
        ) numbers
        """
    
    @staticmethod
    def unique_timestamp_suffix() -> str:
        """Generate unique string for test isolation."""
        return f"test_{int(time.time())}_{hash(time.time()) % 10000:04d}"


class QueryValidator:
    """Validator for checking query results meet expected patterns."""
    
    @staticmethod
    def validate_simple_result(result) -> bool:
        """Validate simple query result structure."""
        try:
            # Check shape
            if hasattr(result, 'shape'):
                assert result.shape == (1, 2), f"Expected (1, 2), got {result.shape}"
            
            # Check columns
            if hasattr(result, 'columns'):
                expected_cols = ['test_col', 'message']
                actual_cols = list(result.columns)
                assert set(actual_cols) == set(expected_cols), f"Expected {expected_cols}, got {actual_cols}"
            
            # Check values
            if hasattr(result, 'to_dict'):
                data = result.to_dict()
                assert data.get('test_col', [None])[0] == 1, "test_col should be 1"
                assert data.get('message', [None])[0] == 'fixed_value', "message should be fixed_value"
            
            return True
            
        except Exception as e:
            print(f"Validation error: {e}")
            return False
    
    @staticmethod
    def validate_data_types_result(result) -> bool:
        """Validate data types query result."""
        try:
            if hasattr(result, 'shape'):
                assert result.shape == (1, 8), f"Expected 1 row, 8 columns, got {result.shape}"
            
            if hasattr(result, 'columns'):
                expected_cols = ['int_col', 'float_col', 'string_col', 'bool_col', 
                               'double_col', 'date_col', 'timestamp_col', 'null_col']
                actual_cols = list(result.columns)
                assert set(actual_cols) == set(expected_cols), f"Column mismatch: {actual_cols}"
            
            if hasattr(result, 'to_dict'):
                data = result.to_dict()
                # Check specific type indicators
                assert data.get('int_col', [None])[0] == 1
                assert data.get('string_col', [None])[0] == 'test_string'
                assert data.get('bool_col', [None])[0] == True
                assert data.get('null_col', [None])[0] is None
            
            return True
            
        except Exception as e:
            print(f"Data types validation error: {e}")
            return False
    
    @staticmethod
    def validate_aggregate_result(result) -> bool:
        """Validate aggregate query result."""
        try:
            if hasattr(result, 'shape'):
                assert result.shape == (1, 5), f"Expected 1 row, 5 columns, got {result.shape}"
            
            if hasattr(result, 'to_dict'):
                data = result.to_dict()
                assert data.get('total_value', [None])[0] == 60  # 10 + 20 + 30
                assert data.get('avg_value', [None])[0] == 20    # (10 + 20 + 30) / 3
                assert data.get('min_value', [None])[0] == 10
                assert data.get('max_value', [None])[0] == 30
                assert data.get('row_count', [None])[0] == 3
            
            return True
            
        except Exception as e:
            print(f"Aggregate validation error: {e}")
            return False
