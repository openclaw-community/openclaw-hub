# AI Gateway Tests

This directory contains the test suite for AI Gateway.

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=aigateway --cov-report=html

# Run specific test file
pytest tests/test_providers.py

# Run specific test
pytest tests/test_providers.py::test_ollama_completion
```

### Test Options

```bash
# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l

# Run only fast tests
pytest -m "not slow"

# Run tests matching pattern
pytest -k "ollama"
```

## Test Structure

```
tests/
├── README.md                 # This file
├── conftest.py              # Shared fixtures
├── test_providers/          # Provider tests
│   ├── test_ollama.py
│   ├── test_openai.py
│   └── test_anthropic.py
├── test_api/                # API endpoint tests
│   ├── test_completions.py
│   ├── test_workflows.py
│   └── test_mcp.py
├── test_orchestration/      # Workflow engine tests
│   ├── test_engine.py
│   └── test_loader.py
└── test_integration/        # End-to-end tests
    └── test_workflows.py
```

## Writing Tests

### Test File Template

```python
"""Tests for [component name]."""

import pytest
from aigateway.providers.ollama import OllamaProvider


@pytest.fixture
def ollama_provider():
    """Fixture providing an Ollama provider instance."""
    return OllamaProvider(base_url="http://localhost:11434")


def test_ollama_completion(ollama_provider):
    """Test basic completion with Ollama provider."""
    response = ollama_provider.complete(
        model="qwen2.5:32b-instruct",
        messages=[{"role": "user", "content": "Hello"}]
    )
    
    assert response is not None
    assert "content" in response
    assert len(response["content"]) > 0


@pytest.mark.asyncio
async def test_ollama_async_completion(ollama_provider):
    """Test async completion with Ollama provider."""
    response = await ollama_provider.complete_async(
        model="qwen2.5:32b-instruct",
        messages=[{"role": "user", "content": "Hello"}]
    )
    
    assert response is not None
```

### Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "ollama_url": "http://localhost:11434",
        "database_url": "sqlite+aiosqlite:///:memory:"
    }


@pytest.fixture
async def test_client():
    """Test FastAPI client."""
    from aigateway.main import app
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Mocking External Services

```python
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_openai_provider_mock():
    """Test OpenAI provider with mocked API."""
    mock_response = {
        "choices": [{"message": {"content": "Hello!"}}]
    }
    
    with patch("openai.AsyncClient") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        
        # Test code here
```

## Test Categories

### Unit Tests

Test individual components in isolation:

```python
def test_token_counter():
    """Test token counting function."""
    from aigateway.providers.base import count_tokens
    
    result = count_tokens("Hello, world!")
    assert result > 0
    assert isinstance(result, int)
```

### Integration Tests

Test multiple components working together:

```python
@pytest.mark.asyncio
async def test_workflow_execution(test_client):
    """Test complete workflow execution."""
    response = await test_client.post(
        "/v1/workflow/summarize",
        json={"input": {"text": "Long text..."}}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "output" in data
```

### End-to-End Tests

Test full system with real providers (marked as slow):

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_ollama_completion():
    """Test with real Ollama instance."""
    # Requires Ollama running on localhost
    provider = OllamaProvider()
    response = await provider.complete(
        model="qwen2.5:32b-instruct",
        messages=[{"role": "user", "content": "Hello"}]
    )
    assert response is not None
```

## Test Markers

Use markers to categorize tests:

```python
# Slow tests (require external services)
@pytest.mark.slow

# Async tests
@pytest.mark.asyncio

# Integration tests
@pytest.mark.integration

# Requires specific setup
@pytest.mark.requires_ollama
@pytest.mark.requires_openai
```

Run specific categories:

```bash
# Skip slow tests
pytest -m "not slow"

# Only integration tests
pytest -m integration

# Only Ollama tests
pytest -m requires_ollama
```

## Coverage

### Viewing Coverage

```bash
# Generate HTML report
pytest --cov=aigateway --cov-report=html

# Open in browser
open htmlcov/index.html
```

### Coverage Goals

- **Overall**: >80%
- **New features**: 100%
- **Critical paths**: 100%
- **Documentation**: All public APIs

## Continuous Integration

Tests run automatically on:
- Every push to `main`
- Every pull request
- Multiple Python versions (3.12, 3.13)

See `.github/workflows/ci.yml` for CI configuration.

## Troubleshooting

### Tests Fail Locally

1. **Check dependencies**: `pip install -r requirements.txt`
2. **Verify Python version**: Should be 3.12+
3. **Check services**: Ollama must be running for some tests
4. **Clear cache**: `pytest --cache-clear`

### Slow Tests

Skip slow tests during development:

```bash
pytest -m "not slow"
```

### Test Database Issues

Tests use in-memory SQLite by default. If you need persistent test database:

```python
@pytest.fixture
def test_db():
    """Persistent test database."""
    db_path = "test_aigateway.db"
    yield db_path
    os.remove(db_path)  # Cleanup
```

## Contributing Tests

When contributing:

1. **Write tests first** (TDD approach)
2. **Test happy path** and error cases
3. **Use fixtures** for common setup
4. **Mock external services** when possible
5. **Document test purpose** in docstring
6. **Keep tests fast** (mock instead of real API calls)

## Resources

- **pytest docs**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **Testing FastAPI**: https://fastapi.tiangolo.com/tutorial/testing/

---

**Test Suite Version**: 1.0.0  
**Last Updated**: 2026-02-12
