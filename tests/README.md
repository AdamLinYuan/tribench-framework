# TriBench Test Suite

This directory contains the test suite for the TriBench framework.

## Structure

- `unit/` - Unit tests for individual components
- `integration/` - Integration tests for system interactions
- `fixtures/` - Test fixtures and mock data

## Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=tribench --cov-report=html

# Run specific test file
pytest tests/unit/test_system.py

# Run specific test
pytest tests/unit/test_system.py::TestSystem::test_system_initialization
```

## Test Markers

Tests are marked with the following markers:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests requiring external systems
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_trino` - Tests requiring Trino
- `@pytest.mark.requires_docker` - Tests requiring Docker

## Writing Tests

Follow these guidelines when writing tests:

1. **One assertion per test** - Keep tests focused
2. **Use fixtures** - Reuse setup code via pytest fixtures
3. **Mock external dependencies** - Unit tests should not depend on external systems
4. **Test edge cases** - Include tests for error conditions
5. **Clear test names** - Use descriptive names like `test_system_starts_successfully`

## Test Coverage

Aim for >80% code coverage. Check coverage reports in `htmlcov/index.html` after running tests with coverage enabled.
