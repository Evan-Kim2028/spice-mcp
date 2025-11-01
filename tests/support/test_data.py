"""
Test data and expected results for validation.
"""
from typing import Dict, List, Any
import polars as pl


class ExpectedResults:
    """Expected results for test queries."""
    
    SIMPLE_QUERY = {
        'shape': (1, 2),
        'columns': ['test_col', 'message'],
        'sample_data': {'test_col': [1], 'message': ['fixed_value']}
    }
    
    DATA_TYPES_QUERY = {
        'shape': (1, 8),
        'columns': ['int_col', 'float_col', 'string_col', 'bool_col', 
                   'double_col', 'date_col', 'timestamp_col', 'null_col'],
        'sample_data': {
            'int_col': [1],
            'float_col': [123.45],
            'string_col': ['test_string'],
            'bool_col': [True],
            'double_col': [123.45],
            'date_col': ['2023-01-01'],
            'timestamp_col': ['2023-01-01 12:00:00'],
            'null_col': [None]
        }
    }
    
    AGGREGATE_QUERY = {
        'shape': (1, 5),
        'columns': ['total_value', 'avg_value', 'min_value', 'max_value', 'row_count'],
        'sample_data': {
            'total_value': [60],
            'avg_value': [20],
            'min_value': [10],
            'max_value': [30],
            'row_count': [3]
        }
    }
    
    TIME_SERIES_QUERY = {
        'min_rows': 1,
        'max_rows': 7,
        'required_columns': ['day', 'block_count'],
        'row_count_should_sum': True  # All block_count values should equal sum
    }


class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def create_sample_dataframe(rows: int = 10) -> pl.DataFrame:
        """Create a sample DataFrame for testing."""
        return pl.DataFrame({
            'id': range(rows),
            'name': [f'row_{i}' for i in range(rows)],
            'value': [i * 1.5 for i in range(rows)],
            'is_even': [i % 2 == 0 for i in range(rows)],
            'timestamp': [f'2023-01-{(i % 28) + 1:02d} 12:00:00' for i in range(rows)]
        })
    
    @staticmethod
    def create_parameter_combinations() -> List[Dict[str, Any]]:
        """Create various parameter combinations for testing."""
        return [
            {},  # No parameters
            {'limit': 5},
            {'limit': 10, 'offset': 5},
            {'string_param': 'test_value'},
            {'int_param': 42, 'float_param': 3.14},
            {'bool_param': True},
            {'date_param': '2023-01-01'},
            {'list_param': [1, 2, 3]},
        ]
    
    @staticmethod
    def create_error_scenarios() -> List[Dict[str, Any]]:
        """Create error scenarios for testing error handling."""
        return [
            {'type': 'invalid_sql', 'sql': 'SELECTTTT INVALID SYNTAX'},
            {'type': 'empty_query', 'sql': ''},
            {'type': 'invalid_parameter', 'sql': 'SELECT {{nonexistent}} as col'},
            {'type': 'division_by_zero', 'sql': 'SELECT 1/0 as error_col'},
            {'type': 'invalid_table', 'sql': 'SELECT * FROM nonexistent_table'},
            {'type': 'invalid_function', 'sql': 'SELECT nonexistent_function() as col'},
        ]


class ResultComparator:
    """Compare actual results with expected results."""
    
    @staticmethod
    def compare_shape(actual, expected_shape: tuple) -> bool:
        """Compare DataFrame shape."""
        if hasattr(actual, 'shape'):
            return actual.shape == expected_shape
        return False
    
    @staticmethod
    def compare_columns(actual, expected_columns: list) -> bool:
        """Compare DataFrame columns."""
        if hasattr(actual, 'columns'):
            actual_cols = list(actual.columns)
            return set(actual_cols) == set(expected_columns)
        return False
    
    @staticmethod
    def compare_data(actual, expected_data: dict) -> bool:
        """Compare DataFrame data values."""
        if not hasattr(actual, 'to_dict'):
            return False
        
        try:
            actual_dict = actual.to_dict()
            for col, expected_vals in expected_data.items():
                actual_vals = actual_dict.get(col, [])
                if len(actual_vals) != len(expected_vals):
                    return False
                
                for i, (actual_val, expected_val) in enumerate(zip(actual_vals, expected_vals)):
                    # Handle float comparisons with tolerance
                    if isinstance(expected_val, float) and isinstance(actual_val, (float, int)):
                        if abs(float(actual_val) - expected_val) > 0.001:
                            return False
                    # Handle null comparisons
                    elif expected_val is None:
                        if actual_val is not None and str(actual_val) != 'null':
                            return False
                    else:
                        if str(actual_val) != str(expected_val):
                            return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_result_patterns(result, pattern_type: str) -> Dict[str, Any]:
        """Validate result against expected patterns."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if not hasattr(result, 'shape'):
                validation['valid'] = False
                validation['errors'].append("Result doesn't have shape attribute")
                return validation
            
            # Basic shape sanity checks
            if result.shape[0] == 0:
                validation['warnings'].append("Result has no rows")
            
            if result.shape[1] == 0:
                validation['valid'] = False
                validation['errors'].append("Result has no columns")
            
            # Column name sanity checks
            if hasattr(result, 'columns'):
                cols = list(result.columns)
                if len(set(cols)) != len(cols):
                    validation['valid'] = False
                    validation['errors'].append("Duplicate column names found")
                
                for col in cols:
                    if not col or not isinstance(col, str):
                        validation['valid'] = False
                        validation['errors'].append(f"Invalid column name: {col}")
            
            return validation
            
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Validation exception: {e}")
            return validation
    
    @staticmethod
    def generate_comparison_report(actual, expected: dict) -> Dict[str, Any]:
        """Generate detailed comparison report."""
        report = {
            'shape_match': True,
            'columns_match': True,
            'data_match': True,
            'details': {}
        }
        
        # Compare shape
        if 'shape' in expected:
            shape_match = ResultComparator.compare_shape(actual, expected['shape'])
            report['shape_match'] = shape_match
            if actual.shape:
                report['details']['shape'] = {
                    'expected': expected['shape'],
                    'actual': actual.shape
                }
        
        # Compare columns
        if 'columns' in expected:
            cols_match = ResultComparator.compare_columns(actual, expected['columns'])
            report['columns_match'] = cols_match
            if hasattr(actual, 'columns'):
                report['details']['columns'] = {
                    'expected': expected['columns'],
                    'actual': list(actual.columns)
                }
        
        # Compare data
        if 'sample_data' in expected:
            data_match = ResultComparator.compare_data(actual, expected['sample_data'])
            report['data_match'] = data_match
            if hasattr(actual, 'to_dict'):
                report['details']['data'] = {
                    'expected': expected['sample_data'],
                    'actual': actual.to_dict()
                }
        
        return report
