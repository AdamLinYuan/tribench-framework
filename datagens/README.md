# Data Generators Directory

This directory contains data generation programs for benchmark datasets.

## Structure

```
datagens/
├── tpch/                  # TPC-H data generator
│   ├── dbgen/            # TPC-H dbgen utility
│   └── scripts/          # Generation scripts
├── tpcds/                # TPC-DS data generator  
│   ├── dsdgen/           # TPC-DS dsdgen utility
│   └── scripts/          # Generation scripts
├── synthetic/            # Synthetic data generators
└── custom/               # Custom data generators
```

## TPC-H Data Generation

```bash
# Generate TPC-H data at scale factor 1
./datagens/tpch/scripts/generate.sh --scale-factor 1 --format parquet --output /path/to/output
```

## TPC-DS Data Generation  

```bash
# Generate TPC-DS data at scale factor 1
./datagens/tpcds/scripts/generate.sh --scale-factor 1 --format parquet --output /path/to/output
```

## Custom Data Generation

Create your own data generators following this pattern:

```python
# datagens/custom/my_generator.py
import argparse
from tribench.datagen import DataGenerator

class MyDataGenerator(DataGenerator):
    def generate(self, scale_factor, output_path, format='parquet'):
        # Implementation here
        pass

if __name__ == "__main__":
    generator = MyDataGenerator()
    generator.run()
```

## Supported Formats

- **Parquet**: Columnar format, optimized for analytics
- **ORC**: Optimized Row Columnar format
- **JSON**: JSON Lines format
- **CSV**: Comma-separated values
- **Iceberg**: Native Iceberg table format
