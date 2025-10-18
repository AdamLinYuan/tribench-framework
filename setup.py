"""Setup script for TriBench package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __version__.py
version_file = Path(__file__).parent / "lib" / "tribench" / "__version__.py"
version = {}
with open(version_file) as f:
    exec(f.read(), version)

# Read README
readme_file = Path(__file__).parent / "README.md"
with open(readme_file, "r", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
with open(requirements_file, "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="tribench",
    version=version["__version__"],
    author="Adam Yuan",
    author_email="your.email@example.com",
    description="A PEEL-inspired benchmarking framework for Apache Trino",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/tribench-framework",
    packages=find_packages(where="lib"),
    package_dir={"": "lib"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: System :: Benchmark",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.2",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tribench=tribench.cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
