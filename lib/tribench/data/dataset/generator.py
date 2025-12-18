"""
TPC-H dataset generator.

Handles generation of TPC-H datasets using Docker-based dbgen.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as csv

from .schema import TPCHSchema

logger = logging.getLogger(__name__)


class TPCHGenerator:
    """Generates TPC-H datasets using Docker-based dbgen."""
    
    DBGEN_IMAGE = "scalytics/tpch:latest"
    
    def __init__(self, output_dir: Path, config: Optional[Dict] = None):
        """
        Initialize TPC-H generator.
        
        Args:
            output_dir: Directory to store generated datasets
            config: Optional configuration dictionary
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}
        self.schema = TPCHSchema()  # Use schema abstraction
    
    def generate(self, scale_factor: float = 1.0, format: str = 'parquet') -> Path:
        """
        Generate TPC-H dataset at specified scale factor.
        
        Args:
            scale_factor: TPC-H scale factor (1 = 1GB)
            format: Output format ('csv' or 'parquet')
            
        Returns:
            Path to generated dataset directory
        """
        sf_str = str(scale_factor).replace('.', '_')
        dataset_name = f"tpch-sf{sf_str}"
        dataset_path = self.output_dir / dataset_name
        dataset_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating TPC-H dataset: {dataset_name}")
        
        # Generate CSV files using dbgen Docker container
        csv_path = dataset_path / "csv"
        csv_path.mkdir(exist_ok=True)
        
        self._run_dbgen(scale_factor, csv_path)
        
        # Convert to Parquet if requested
        if format == 'parquet':
            logger.info("Converting CSV to Parquet...")
            parquet_path = dataset_path / "parquet"
            parquet_path.mkdir(exist_ok=True)
            self._convert_to_parquet(csv_path, parquet_path)
            return parquet_path
        
        return csv_path
    
    def _run_dbgen(self, scale_factor: float, output_dir: Path) -> None:
        """Run dbgen in Docker container to generate CSV files."""
        try:
            # Check if Docker is available
            subprocess.run(['docker', '--version'], 
                         check=True, 
                         capture_output=True)
            
            # Run dbgen container
            cmd = [
                'docker', 'run', '--rm',
                '-v', f'{output_dir.absolute()}:/data',
                self.DBGEN_IMAGE,
                '-s', str(scale_factor)
            ]
            
            logger.info(f"Running dbgen: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if result.stdout:
                logger.debug(f"dbgen output: {result.stdout}")
            
            logger.info(f"Successfully generated TPC-H SF{scale_factor} data")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run dbgen: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise RuntimeError(f"Failed to generate TPC-H data: {e}")
        except FileNotFoundError:
            raise RuntimeError("Docker is not available. Please install Docker to generate datasets.")
    
    def _convert_to_parquet(self, csv_dir: Path, parquet_dir: Path) -> None:
        """Convert CSV files to Parquet format."""
        for csv_file in csv_dir.glob("*.tbl"):
            table_name = csv_file.stem
            
            if table_name not in self.schema.get_tables():
                logger.warning(f"Unknown table: {table_name}, skipping")
                continue
            
            logger.info(f"Converting {table_name}.tbl to Parquet...")
            
            try:
                # Get schema for this table
                table_schema = self.schema.get_schema(table_name)
                
                # Read CSV with pipe delimiter (TPC-H format)
                # TPC-H .tbl files don't have headers, so we need to specify column names
                # TPC-H files have trailing delimiter creating an extra empty column
                # We add a dummy column name and remove it after reading
                column_names = [field.name for field in table_schema] + ['_dummy']
                
                read_options = csv.ReadOptions(
                    autogenerate_column_names=False,
                    column_names=column_names
                )
                table = csv.read_csv(
                    csv_file,
                    read_options=read_options,
                    parse_options=csv.ParseOptions(
                        delimiter='|',
                        ignore_empty_lines=True
                    ),
                    convert_options=csv.ConvertOptions(
                        column_types=table_schema,
                        strings_can_be_null=True
                    )
                )
                
                # Remove the dummy column created by trailing delimiter
                table = table.drop(['_dummy'])
                
                # Write Parquet file
                parquet_file = parquet_dir / f"{table_name}.parquet"
                pq.write_table(table, parquet_file, compression='snappy')
                
                logger.info(f"Created {parquet_file.name} ({table.num_rows} rows)")
                
            except Exception as e:
                logger.error(f"Failed to convert {table_name}: {e}")
                raise
