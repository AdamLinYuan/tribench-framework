"""Unit tests for dataset management module."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from tribench.data.dataset import (
    DatasetMetadata,
    DatasetValidator,
    TPCHGenerator,
    TrinoDataLoader,
    DatasetRegistry
)


class TestDatasetMetadata:
    """Tests for DatasetMetadata dataclass."""
    
    def test_metadata_creation(self):
        """Test creating dataset metadata."""
        metadata = DatasetMetadata(
            name="test-dataset",
            type="generated",
            format="parquet",
            scale_factor=1.0,
            size_bytes=1024000,
            location="/path/to/dataset",
            tables=["table1", "table2"],
            row_counts={"table1": 1000, "table2": 2000},
            checksums={"table1": "abc123", "table2": "def456"},
            properties={"key": "value"},
            created_at="2025-01-01T00:00:00",
            generator="tpch-dbgen"
        )
        
        assert metadata.name == "test-dataset"
        assert metadata.type == "generated"
        assert metadata.format == "parquet"
        assert metadata.scale_factor == 1.0
        assert len(metadata.tables) == 2
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = DatasetMetadata(
            name="test",
            type="static",
            format="csv",
            scale_factor=None,
            size_bytes=1024,
            location="/path",
            tables=["t1"],
            row_counts={"t1": 100},
            checksums={"t1": "hash"},
            properties={},
            created_at="2025-01-01"
        )
        
        data = metadata.to_dict()
        assert isinstance(data, dict)
        assert data['name'] == "test"
        assert data['type'] == "static"
    
    def test_metadata_from_dict(self):
        """Test creating metadata from dictionary."""
        data = {
            'name': 'test',
            'type': 'generated',
            'format': 'parquet',
            'scale_factor': 1.0,
            'size_bytes': 1024,
            'location': '/path',
            'tables': ['t1'],
            'row_counts': {'t1': 100},
            'checksums': {'t1': 'hash'},
            'properties': {},
            'created_at': '2025-01-01',
            'generator': 'dbgen'
        }
        
        metadata = DatasetMetadata.from_dict(data)
        assert metadata.name == 'test'
        assert metadata.generator == 'dbgen'


class TestDatasetValidator:
    """Tests for DatasetValidator."""
    
    def test_expected_row_counts(self):
        """Test expected TPC-H row counts are defined."""
        assert 'tiny' in DatasetValidator.TPCH_ROW_COUNTS
        assert '1' in DatasetValidator.TPCH_ROW_COUNTS
        
        tiny_counts = DatasetValidator.TPCH_ROW_COUNTS['tiny']
        assert 'nation' in tiny_counts
        assert tiny_counts['nation'] == 25
        assert 'lineitem' in tiny_counts
        assert tiny_counts['lineitem'] == 60175
    
    def test_compute_file_checksum(self):
        """Test computing file checksums."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test data")
            temp_file = Path(f.name)
        
        try:
            checksum = DatasetValidator.compute_file_checksum(temp_file)
            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA256 hex digest length
        finally:
            temp_file.unlink()
    
    @patch('tribench.data.dataset.pq.read_table')
    def test_validate_parquet_file_success(self, mock_read_table):
        """Test successful Parquet file validation."""
        # Mock PyArrow table
        mock_table = Mock()
        mock_table.num_rows = 1000
        mock_table.schema = Mock()
        mock_table.schema.__str__ = Mock(return_value="schema")
        mock_read_table.return_value = mock_table
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            temp_file = Path(f.name)
        
        try:
            result = DatasetValidator.validate_parquet_file(temp_file)
            assert result['valid'] is True
            assert result['row_count'] == 1000
            assert 'checksum' in result
            assert 'size_bytes' in result
        finally:
            temp_file.unlink()
    
    @patch('tribench.data.dataset.pq.read_table')
    def test_validate_parquet_file_failure(self, mock_read_table):
        """Test Parquet file validation failure."""
        mock_read_table.side_effect = Exception("Read error")
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            temp_file = Path(f.name)
        
        try:
            result = DatasetValidator.validate_parquet_file(temp_file)
            assert result['valid'] is False
            assert 'error' in result
        finally:
            temp_file.unlink()


class TestTPCHGenerator:
    """Tests for TPCHGenerator."""
    
    def test_generator_initialization(self):
        """Test TPCHGenerator initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = TPCHGenerator(output_dir)
            
            assert generator.output_dir == output_dir
            assert output_dir.exists()
    
    def test_tpch_schemas_defined(self):
        """Test that TPC-H schemas are properly defined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TPCHGenerator(Path(tmpdir))
            schemas = generator._get_tpch_schemas()
            
            expected_tables = ['nation', 'region', 'customer', 'supplier',
                             'part', 'partsupp', 'orders', 'lineitem']
            
            for table in expected_tables:
                assert table in schemas
                assert len(schemas[table]) > 0  # Has fields
    
    @patch('tribench.data.dataset.subprocess.run')
    def test_run_dbgen_success(self, mock_run):
        """Test successful dbgen execution."""
        mock_run.return_value = Mock(stdout="", stderr="")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = TPCHGenerator(output_dir)
            
            csv_path = output_dir / "csv"
            csv_path.mkdir()
            
            # Should not raise exception
            generator._run_dbgen(1.0, csv_path)
            
            # Verify docker command was called
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert 'docker' in call_args
            assert '-s' in call_args
    
    @patch('tribench.data.dataset.subprocess.run')
    def test_run_dbgen_docker_not_available(self, mock_run):
        """Test dbgen when Docker is not available."""
        mock_run.side_effect = FileNotFoundError("docker not found")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = TPCHGenerator(output_dir)
            csv_path = output_dir / "csv"
            csv_path.mkdir()
            
            with pytest.raises(RuntimeError, match="Docker is not available"):
                generator._run_dbgen(1.0, csv_path)


class TestTrinoDataLoader:
    """Tests for TrinoDataLoader."""
    
    def test_loader_initialization(self):
        """Test TrinoDataLoader initialization."""
        params = {
            'host': 'localhost',
            'port': 8080,
            'user': 'admin'
        }
        
        loader = TrinoDataLoader(params)
        assert loader.connection_params == params
    
    def test_arrow_to_trino_type_mappings(self):
        """Test PyArrow to Trino type conversions."""
        import pyarrow as pa
        
        params = {'host': 'localhost', 'port': 8080}
        loader = TrinoDataLoader(params)
        
        assert loader._arrow_to_trino_type(pa.int32()) == "INTEGER"
        assert loader._arrow_to_trino_type(pa.int64()) == "BIGINT"
        assert loader._arrow_to_trino_type(pa.string()) == "VARCHAR"
        assert loader._arrow_to_trino_type(pa.date32()) == "DATE"
        
        # Test decimal
        decimal_type = pa.decimal128(15, 2)
        assert "DECIMAL" in loader._arrow_to_trino_type(decimal_type)
    
    def test_generate_create_table_ddl(self):
        """Test generating CREATE TABLE DDL."""
        import pyarrow as pa
        
        schema = pa.schema([
            ('id', pa.int32()),
            ('name', pa.string()),
            ('value', pa.decimal128(10, 2))
        ])
        
        params = {'host': 'localhost', 'port': 8080}
        loader = TrinoDataLoader(params)
        
        ddl = loader._generate_create_table_ddl('test_table', schema)
        
        assert 'CREATE TABLE test_table' in ddl
        assert 'id INTEGER' in ddl
        assert 'name VARCHAR' in ddl
        assert 'value DECIMAL' in ddl


class TestDatasetRegistry:
    """Tests for DatasetRegistry."""
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = DatasetRegistry(registry_path)
            
            assert registry.registry_path == registry_path
            assert len(registry.list()) == 0
    
    def test_register_and_get_dataset(self):
        """Test registering and retrieving datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = DatasetRegistry(registry_path)
            
            metadata = DatasetMetadata(
                name="test-ds",
                type="generated",
                format="parquet",
                scale_factor=1.0,
                size_bytes=1024,
                location="/path",
                tables=["t1"],
                row_counts={"t1": 100},
                checksums={"t1": "hash"},
                properties={},
                created_at=datetime.now().isoformat()
            )
            
            registry.register(metadata)
            
            retrieved = registry.get("test-ds")
            assert retrieved is not None
            assert retrieved.name == "test-ds"
            assert retrieved.format == "parquet"
    
    def test_list_datasets(self):
        """Test listing all datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = DatasetRegistry(registry_path)
            
            # Register multiple datasets
            for i in range(3):
                metadata = DatasetMetadata(
                    name=f"dataset-{i}",
                    type="generated",
                    format="parquet",
                    scale_factor=1.0,
                    size_bytes=1024,
                    location=f"/path{i}",
                    tables=["t1"],
                    row_counts={"t1": 100},
                    checksums={"t1": "hash"},
                    properties={},
                    created_at=datetime.now().isoformat()
                )
                registry.register(metadata)
            
            datasets = registry.list()
            assert len(datasets) == 3
    
    def test_delete_dataset(self):
        """Test deleting dataset from registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = DatasetRegistry(registry_path)
            
            metadata = DatasetMetadata(
                name="to-delete",
                type="generated",
                format="parquet",
                scale_factor=1.0,
                size_bytes=1024,
                location="/path",
                tables=["t1"],
                row_counts={"t1": 100},
                checksums={"t1": "hash"},
                properties={},
                created_at=datetime.now().isoformat()
            )
            
            registry.register(metadata)
            assert registry.get("to-delete") is not None
            
            result = registry.delete("to-delete")
            assert result is True
            assert registry.get("to-delete") is None
    
    def test_update_dataset(self):
        """Test updating dataset metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = DatasetRegistry(registry_path)
            
            metadata = DatasetMetadata(
                name="update-test",
                type="generated",
                format="parquet",
                scale_factor=1.0,
                size_bytes=1024,
                location="/path",
                tables=["t1"],
                row_counts={"t1": 100},
                checksums={"t1": "hash"},
                properties={},
                created_at=datetime.now().isoformat()
            )
            
            registry.register(metadata)
            
            # Update metadata
            metadata.size_bytes = 2048
            registry.update("update-test", metadata)
            
            updated = registry.get("update-test")
            assert updated.size_bytes == 2048
    
    def test_registry_persistence(self):
        """Test that registry persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            
            # Create and register
            registry1 = DatasetRegistry(registry_path)
            metadata = DatasetMetadata(
                name="persist-test",
                type="generated",
                format="parquet",
                scale_factor=1.0,
                size_bytes=1024,
                location="/path",
                tables=["t1"],
                row_counts={"t1": 100},
                checksums={"t1": "hash"},
                properties={},
                created_at=datetime.now().isoformat()
            )
            registry1.register(metadata)
            
            # Create new registry instance and verify data persisted
            registry2 = DatasetRegistry(registry_path)
            retrieved = registry2.get("persist-test")
            
            assert retrieved is not None
            assert retrieved.name == "persist-test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
