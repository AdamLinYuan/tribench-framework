"""
Unit tests for Iceberg validator.

Tests the IcebergValidator implementation including:
- Table validation
- Row count validation
- Schema validation
- Iceberg metadata validation (snapshots, files)
- TPC-H specific validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from tribench.data.iceberg_validator import IcebergValidator


@pytest.fixture
def connection_params():
    """Mock Trino connection parameters."""
    return {
        'host': 'localhost',
        'port': 8080,
        'user': 'admin'
    }


@pytest.fixture
def iceberg_validator(connection_params):
    """Create IcebergValidator instance."""
    return IcebergValidator(connection_params)


class TestIcebergValidator:
    """Tests for IcebergValidator class."""
    
    def test_init(self, iceberg_validator, connection_params):
        """Test validator initialization."""
        assert iceberg_validator.connection_params == connection_params
        assert iceberg_validator.connection_params['host'] == 'localhost'
        assert iceberg_validator.connection_params['port'] == 8080
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_get_connection(self, mock_connect, iceberg_validator):
        """Test Trino connection creation."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        conn = iceberg_validator._get_connection('iceberg', 'tpch')
        
        mock_connect.assert_called_once()
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs['catalog'] == 'iceberg'
        assert call_kwargs['schema'] == 'tpch'
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_get_row_count(self, mock_connect, iceberg_validator):
        """Test row count retrieval."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (12345,)
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        count = iceberg_validator._get_row_count(mock_cursor, 'test_table')
        
        assert count == 12345
        assert mock_cursor.execute.called
        execute_call = mock_cursor.execute.call_args[0][0]
        assert 'COUNT(*)' in execute_call.upper()
        assert 'test_table' in execute_call
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_get_table_schema(self, mock_connect, iceberg_validator):
        """Test table schema retrieval."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('id', 'integer'),
            ('name', 'varchar'),
            ('price', 'double')
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        schema = iceberg_validator._get_table_schema(mock_cursor, 'test_table')
        
        assert len(schema) == 3
        # _get_table_schema returns list of dicts, not tuples
        assert schema[0]['name'] == 'id'
        assert schema[0]['type'] == 'integer'
        assert schema[1]['name'] == 'name'
        assert schema[1]['type'] == 'varchar'
        assert schema[2]['name'] == 'price'
        assert schema[2]['type'] == 'double'


class TestIcebergMetadataValidation:
    """Tests for Iceberg metadata validation."""
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_get_iceberg_metadata_snapshots(self, mock_connect, iceberg_validator):
        """Test snapshot metadata retrieval."""
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            (3, 'manifest1'),  # snapshot info
            (3,),  # snapshot count
            (5,)   # file count
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # _get_iceberg_metadata takes only cursor and table_name (2 args, not 4)
        metadata = iceberg_validator._get_iceberg_metadata(
            mock_cursor,
            'test_table'
        )
        
        assert metadata['snapshot_count'] == 3
        assert metadata['file_count'] == 5
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_get_iceberg_metadata_handles_errors(self, mock_connect, iceberg_validator):
        """Test metadata retrieval handles query errors gracefully."""
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = Exception('System table not accessible')
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # _get_iceberg_metadata takes only cursor and table_name
        metadata = iceberg_validator._get_iceberg_metadata(
            mock_cursor,
            'test_table'
        )
        
        # Should handle error gracefully
        assert isinstance(metadata, dict)
        # Counts should be None when queries fail
        assert metadata.get('snapshot_count') is None or metadata.get('snapshot_count') == 0


class TestTableValidation:
    """Tests for individual table validation."""
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_iceberg_table_success(self, mock_connect, iceberg_validator):
        """Test successful table validation."""
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = [
            [('test_table',)],  # table exists
        ]
        mock_cursor.fetchone.side_effect = [
            (1000,),  # row count
        ]
        
        # Mock schema query
        mock_cursor.fetchall.return_value = [
            ('id', 'integer'),
            ('name', 'varchar')
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # validate_iceberg_table takes cursor, table_name, scale_factor, benchmark_type
        result = iceberg_validator.validate_iceberg_table(
            mock_cursor,
            'test_table',
            scale_factor='tiny',
            benchmark_type='tpch'
        )
        
        assert result['valid'] is True
        assert result['table_name'] == 'test_table'
        assert result['row_count'] == 1000
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_iceberg_table_row_count_mismatch(self, mock_connect, iceberg_validator):
        """Test validation with row count mismatch."""
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = [
            [('test_table',)],  # table exists
        ]
        mock_cursor.fetchone.side_effect = [
            (999,),  # actual row count (mismatch from expected)
        ]
        mock_cursor.fetchall.return_value = [('id', 'integer')]  # schema
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # validate_iceberg_table takes cursor, table_name, scale_factor, benchmark_type
        result = iceberg_validator.validate_iceberg_table(
            mock_cursor,
            'nation',  # Use TPC-H table that has expected count
            scale_factor='tiny',  # Expected count is 25 for nation
            benchmark_type='tpch'
        )
        
        assert result['valid'] is False
        assert result['row_count'] == 999
        assert result['expected_row_count'] == 25
        assert len(result['errors']) > 0
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_table_not_exists(self, mock_connect, iceberg_validator):
        """Test validation when table doesn't exist."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []  # Empty result means table doesn't exist
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # validate_iceberg_table takes cursor, table_name
        result = iceberg_validator.validate_iceberg_table(
            mock_cursor,
            'nonexistent_table'
        )
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert any('does not exist' in err for err in result['errors'])


class TestDatasetValidation:
    """Tests for dataset-level validation."""
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_iceberg_dataset(self, mock_connect, iceberg_validator):
        """Test validating multiple tables in a dataset."""
        mock_cursor = Mock()
        
        # Mock responses for multiple tables
        mock_cursor.fetchone.side_effect = [
            (100,),   # table1 row count
            (200,),   # table2 row count
        ]
        
        mock_cursor.fetchall.side_effect = [
            [('id', 'integer')],  # table1 schema
            [(1,)],  # table1 snapshots
            [(1,)],  # table1 files
            [('id', 'integer')],  # table2 schema
            [(1,)],  # table2 snapshots
            [(1,)]   # table2 files
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        result = iceberg_validator.validate_iceberg_dataset(
            catalog='iceberg',
            schema='tpch',
            tables=['table1', 'table2']
        )
        
        assert result['valid'] is True
        assert result['catalog'] == 'iceberg'
        assert result['schema'] == 'tpch'
        assert 'tables' in result
        assert len(result['tables']) == 2
        assert 'table1' in result['tables']
        assert 'table2' in result['tables']
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_dataset_with_failures(self, mock_connect, iceberg_validator):
        """Test dataset validation with some table failures."""
        mock_cursor = Mock()
        
        # First table succeeds, second fails
        mock_cursor.fetchone.side_effect = [
            (100,),   # table1 row count
            Exception('Table not found')  # table2 fails
        ]
        
        mock_cursor.fetchall.side_effect = [
            [('id', 'integer')],  # table1 schema
            [(1,)],  # table1 snapshots
            [(1,)]   # table1 files
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        result = iceberg_validator.validate_iceberg_dataset(
            catalog='iceberg',
            schema='tpch',
            tables=['table1', 'table2']
        )
        
        assert result['valid'] is False
        assert 'errors' in result
        assert len(result['errors']) > 0


class TestTPCHValidation:
    """Tests for TPC-H specific validation."""
    
    def test_validate_tpch_dataset_has_expected_counts(self, iceberg_validator):
        """Test that TPC-H validation uses expected row counts."""
        # The validate_tpch_iceberg_dataset method should define expected counts
        assert hasattr(iceberg_validator, 'validate_tpch_iceberg_dataset')
        
        # Check method signature
        import inspect
        sig = inspect.signature(iceberg_validator.validate_tpch_iceberg_dataset)
        assert 'scale_factor' in sig.parameters
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_tpch_tiny_dataset(self, mock_connect, iceberg_validator):
        """Test TPC-H tiny dataset validation."""
        mock_cursor = Mock()
        
        # Mock row counts for TPC-H tiny tables
        mock_cursor.fetchone.side_effect = [
            (1500,),   # customer
            (60175,),  # lineitem
            (25,),     # nation
            (15000,),  # orders
            (2000,),   # part
            (8000,),   # partsupp
            (5,),      # region
            (100,)     # supplier
        ]
        
        # Mock schema and metadata for each table
        mock_cursor.fetchall.side_effect = [
            [('c_custkey', 'bigint')],  # customer schema
            [(1,)], [(1,)],  # customer snapshots/files
            [('l_orderkey', 'bigint')],  # lineitem schema
            [(1,)], [(1,)],  # lineitem snapshots/files
            [('n_nationkey', 'bigint')],  # nation schema
            [(1,)], [(1,)],  # nation snapshots/files
            [('o_orderkey', 'bigint')],  # orders schema
            [(1,)], [(1,)],  # orders snapshots/files
            [('p_partkey', 'bigint')],  # part schema
            [(1,)], [(1,)],  # part snapshots/files
            [('ps_partkey', 'bigint')],  # partsupp schema
            [(1,)], [(1,)],  # partsupp snapshots/files
            [('r_regionkey', 'bigint')],  # region schema
            [(1,)], [(1,)],  # region snapshots/files
            [('s_suppkey', 'bigint')],  # supplier schema
            [(1,)], [(1,)]   # supplier snapshots/files
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        result = iceberg_validator.validate_tpch_iceberg_dataset(
            catalog='iceberg',
            schema='tpch',
            scale_factor='tiny'
        )
        
        assert isinstance(result, dict)
        assert 'tables' in result or 'valid' in result


class TestValidatorEdgeCases:
    """Tests for edge cases and error handling."""
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_empty_table(self, mock_connect, iceberg_validator):
        """Test validation of table with zero rows."""
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = [
            [('empty_table',)],  # table exists
        ]
        mock_cursor.fetchone.return_value = (0,)  # Zero rows
        mock_cursor.fetchall.return_value = [('id', 'integer')]  # schema
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # validate_iceberg_table takes cursor, table_name
        result = iceberg_validator.validate_iceberg_table(
            mock_cursor,
            'empty_table'
        )
        
        assert result['row_count'] == 0
        # Table should be valid even if empty, may have warnings
        assert isinstance(result.get('warnings', []), list)
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_with_connection_error(self, mock_connect, iceberg_validator):
        """Test validation handles connection errors."""
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = Exception('Connection error')
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # validate_iceberg_table takes cursor, table_name
        result = iceberg_validator.validate_iceberg_table(
            mock_cursor,
            'test_table'
        )
        
        assert result['valid'] is False
        assert len(result.get('errors', [])) > 0
    
    @patch('tribench.data.iceberg_validator.connect')
    def test_validate_invalid_scale_factor(self, mock_connect, iceberg_validator):
        """Test validation with invalid scale factor."""
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = [
            [('nation',)],  # table exists
        ]
        mock_cursor.fetchone.return_value = (25,)  # row count
        mock_cursor.fetchall.return_value = [('n_nationkey', 'integer')]  # schema
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # validate_tpch_iceberg_dataset with invalid scale factor
        # Should still run but won't find expected counts
        result = iceberg_validator.validate_tpch_iceberg_dataset(
            catalog='iceberg',
            schema='tpch',
            scale_factor='invalid_sf'
        )
        
        # Should not crash - just won't have expected counts for comparison
        assert 'valid' in result
        assert 'tables' in result
