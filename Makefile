.PHONY: help install test lint format clean run-tests coverage

help:
	@echo "TriBench Development Commands"
	@echo "=============================="
	@echo "make install      - Install development dependencies"
	@echo "make test         - Run all tests"
	@echo "make lint         - Run code linters"
	@echo "make format       - Format code with black"
	@echo "make coverage     - Run tests with coverage report"
	@echo "make clean        - Clean build artifacts"
	@echo "make cli          - Run CLI (usage: make cli ARGS='sys status trino')"

install:
	pip install -r requirements.txt
	pip install -e .

test:
	PYTHONPATH=lib:$$PYTHONPATH pytest tests/

lint:
	flake8 lib/tribench tests/
	# mypy lib/tribench  # Enable when ready

format:
	black lib/tribench tests/

coverage:
	PYTHONPATH=lib:$$PYTHONPATH pytest --cov=tribench --cov-report=html --cov-report=term tests/
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

cli:
	PYTHONPATH=lib:$$PYTHONPATH python3 -m tribench.cli.base $(ARGS)

# Development helpers
dev-setup:
	@echo "Setting up development environment..."
	python3 -m venv venv || true
	@echo "Activate virtual environment with: source venv/bin/activate"
	@echo "Then run: make install"

check: lint test
	@echo "All checks passed!"
