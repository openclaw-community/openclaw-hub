# Contributing to AI Gateway

Thank you for your interest in contributing to AI Gateway! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to a Code of Conduct (see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)). By participating, you are expected to uphold this code.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/openclaw-hub.git
   cd openclaw-hub
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/openclaw-community/openclaw-hub.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git
- Virtual environment tool (venv)

### Installation

1. **Create virtual environment**:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install development dependencies**:
   ```bash
   pip install pytest pytest-cov ruff mypy
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the server**:
   ```bash
   uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload
   ```

6. **Verify installation**:
   ```bash
   curl http://localhost:8080/health
   ```

## Making Changes

### Branching Strategy

- `main` - Production-ready code
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `docs/*` - Documentation updates

### Creating a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(providers): add Google Gemini provider"
git commit -m "fix(ollama): handle connection timeout gracefully"
git commit -m "docs(readme): update installation instructions"
```

## Pull Request Process

1. **Update your branch**:
   ```bash
   git checkout main
   git pull upstream main
   git checkout feature/your-feature-name
   git rebase main
   ```

2. **Run tests locally**:
   ```bash
   pytest
   ruff check .
   mypy aigateway/
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request**:
   - Go to GitHub and create a PR from your fork
   - Fill out the PR template completely
   - Link related issues (e.g., "Fixes #123")
   - Add appropriate labels

5. **Code Review**:
   - Address reviewer feedback
   - Push additional commits as needed
   - Request re-review when ready

6. **Merge**:
   - Maintainers will merge when approved
   - PR branch will be deleted automatically

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use [Ruff](https://github.com/astral-sh/ruff) for linting
- Maximum line length: 100 characters
- Use type hints for all functions

### Code Organization

```python
"""Module docstring explaining purpose."""

from typing import Optional
import logging

# Constants at module level
DEFAULT_TIMEOUT = 30

# Type aliases
RequestType = dict[str, any]


class MyClass:
    """Class docstring explaining purpose.
    
    Attributes:
        name: Description of attribute
        timeout: Description of attribute
    """
    
    def __init__(self, name: str, timeout: int = DEFAULT_TIMEOUT):
        """Initialize MyClass.
        
        Args:
            name: Name of the instance
            timeout: Connection timeout in seconds
        """
        self.name = name
        self.timeout = timeout
    
    def process(self, data: RequestType) -> Optional[str]:
        """Process the data and return result.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Processed result string, or None if processing failed
            
        Raises:
            ValueError: If data is invalid
        """
        pass
```

### Naming Conventions

- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`

### Type Hints

Always use type hints:

```python
# Good
def calculate_cost(tokens: int, rate: float) -> float:
    return tokens * rate

# Bad
def calculate_cost(tokens, rate):
    return tokens * rate
```

### Error Handling

```python
# Good - Specific exceptions
try:
    result = risky_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
except ValueError as e:
    logger.warning(f"Invalid value: {e}")
    return None

# Bad - Bare except
try:
    result = risky_operation()
except:
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use structured logging
logger.info("Processing request", extra={
    "request_id": req_id,
    "model": model_name,
    "tokens": token_count
})
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aigateway --cov-report=html

# Run specific test file
pytest tests/test_providers.py

# Run specific test
pytest tests/test_providers.py::test_ollama_completion
```

### Writing Tests

Create test files in `tests/` directory:

```python
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


def test_ollama_error_handling(ollama_provider):
    """Test error handling with invalid model."""
    with pytest.raises(ValueError):
        ollama_provider.complete(
            model="nonexistent-model",
            messages=[{"role": "user", "content": "Hello"}]
        )
```

### Test Coverage

- Aim for >80% coverage
- All new features must include tests
- Bug fixes should include regression tests

## Documentation

### Code Documentation

- All modules, classes, and functions must have docstrings
- Use Google-style docstrings
- Include examples for complex functions

### User Documentation

- Update README.md for user-facing changes
- Add examples to `examples/` for new features
- Update `docs/MCP-INTEGRATION.md` for tool changes

### API Documentation

FastAPI auto-generates API docs:
- Visit http://localhost:8080/docs for interactive docs
- Ensure all endpoints have proper descriptions

## Project Structure

```
openclaw-hub/
├── aigateway/              # Main package
│   ├── api/               # API endpoints
│   ├── providers/         # LLM provider implementations
│   ├── orchestration/     # Workflow engine
│   ├── mcp/              # MCP integration
│   └── storage/          # Database models
├── scripts/              # Install and uninstall scripts
├── examples/             # Example YAML workflow definitions
├── tests/               # Test suite
├── docs/                # Additional documentation
└── .github/             # GitHub configuration
    ├── workflows/       # CI/CD GitHub Actions
    └── ISSUE_TEMPLATE/  # Issue templates
```

## Areas for Contribution

### Good First Issues

Look for issues labeled `good-first-issue`:
- Documentation improvements
- Adding examples
- Minor bug fixes
- Test coverage improvements

### High-Priority Areas

- **New Providers**: Add support for more LLM providers (Google, Cohere, etc.)
- **Workflow Features**: Advanced orchestration capabilities
- **MCP Servers**: Create new tool integrations
- **Performance**: Caching, connection pooling, optimization
- **Documentation**: Tutorials, guides, examples

### Feature Requests

Before working on a major feature:
1. Open an issue to discuss the feature
2. Wait for maintainer feedback
3. Create a design document if needed
4. Get approval before starting implementation

## Questions?

- **Issues**: Open a GitHub issue for bugs or questions
- **Discussions**: Use GitHub Discussions for general questions
- **Security**: See [SECURITY.md](SECURITY.md) for security concerns

## Recognition

Contributors will be:
- Added to the project's contributor list
- Mentioned in release notes for significant contributions
- Credited in documentation for major features

Thank you for contributing to AI Gateway! 🚀
