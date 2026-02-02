# Contributing to AgentTrace

Thank you for your interest in contributing to AgentTrace! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)
- [Questions and Support](#questions-and-support)

## Code of Conduct

AgentTrace follows a code of conduct that we expect all contributors to adhere to:

- **Be respectful** - Treat everyone with respect and kindness
- **Be collaborative** - Work together constructively and help others
- **Be professional** - Keep discussions focused and productive
- **Be inclusive** - Welcome contributors of all backgrounds and experience levels

## Getting Started

### Prerequisites

Before you begin, make sure you have:

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Docker and Docker Compose
- Node.js 18+ (for web UI development)
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/AgentTrace.git
cd AgentTrace
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/jimmybentley/AgentTrace.git
```

### Set Up Development Environment

```bash
# Install all dependencies with development tools
make dev

# Start the database
make docker-up

# Run migrations
make migrate

# Verify everything works
make test
```

## Development Workflow

### 1. Create a Feature Branch

Always create a new branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding or improving tests

### 2. Make Your Changes

- Write clear, concise code
- Follow the code style guidelines (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run unit tests
make test

# Run integration tests
make test-integration

# Run linter
make lint

# Format code
make format
```

### 4. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: add support for new framework integration"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 5. Keep Your Fork Updated

```bash
git fetch upstream
git rebase upstream/main
```

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python

AgentTrace uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Format code
make format

# Check for issues
make lint
```

**Guidelines:**

- Use type hints for all function signatures
- Write docstrings for public APIs (Google style)
- Keep functions focused and small
- Use descriptive variable names
- Avoid global state

**Example:**

```python
from typing import Optional

def process_trace(trace_id: str, timeout: Optional[int] = None) -> dict:
    """Process a trace and return analysis results.

    Args:
        trace_id: The unique identifier for the trace
        timeout: Optional timeout in seconds

    Returns:
        Dictionary containing analysis results

    Raises:
        TraceNotFoundError: If trace_id does not exist
        TimeoutError: If processing exceeds timeout
    """
    # Implementation
    pass
```

### TypeScript/JavaScript

For web UI development:

```bash
cd web

# Lint code
npm run lint

# Format code
npm run lint -- --fix
```

**Guidelines:**

- Use TypeScript for type safety
- Use functional components and hooks in React
- Keep components small and focused
- Use meaningful component and variable names

## Testing

### Writing Tests

#### Python Tests

Use pytest for testing:

```python
# packages/core/tests/test_models.py
import pytest
from agenttrace_core.models import Trace

def test_trace_creation():
    """Test creating a trace with valid data."""
    trace = Trace(
        trace_id="test-123",
        name="test_trace",
        service_name="test"
    )
    assert trace.trace_id == "test-123"
    assert trace.name == "test_trace"

def test_trace_validation():
    """Test trace validation for invalid data."""
    with pytest.raises(ValueError):
        Trace(trace_id="", name="test")
```

#### TypeScript Tests

Use Vitest for frontend testing:

```typescript
// web/src/components/TraceList.test.tsx
import { render, screen } from '@testing-library/react';
import { TraceList } from './TraceList';

describe('TraceList', () => {
  it('renders trace items', () => {
    const traces = [
      { trace_id: '1', name: 'Test Trace' }
    ];
    render(<TraceList traces={traces} />);
    expect(screen.getByText('Test Trace')).toBeInTheDocument();
  });
});
```

### Running Tests

```bash
# All tests
make test

# Integration tests (requires database)
make test-integration

# Specific package
pytest packages/core/tests -v

# With coverage
pytest --cov=agenttrace_core --cov-report=html
```

### Test Coverage

Aim for:
- **80%+ coverage** for new code
- **100% coverage** for critical paths
- **All public APIs** should have tests

## Pull Request Process

### Before Submitting

Checklist:
- [ ] Code follows style guidelines
- [ ] All tests pass (`make test`)
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is rebased on latest main

### PR Description

Include in your PR description:

1. **Summary** - What does this PR do?
2. **Motivation** - Why is this change needed?
3. **Changes** - List of key changes
4. **Testing** - How was this tested?
5. **Screenshots** - For UI changes
6. **Related Issues** - Link to issues this PR addresses

**Example:**

```markdown
## Summary
Add support for Semantic Kernel framework integration

## Motivation
Users have requested support for Semantic Kernel. This is a popular
framework and would expand AgentTrace's usefulness.

## Changes
- Add `SemanticKernelNormalizer` in `packages/ingestion/`
- Add auto-instrumentation in SDK
- Add tests and documentation

## Testing
- Added unit tests for normalizer
- Added integration test with sample SK application
- Manually tested with real SK app

## Related Issues
Closes #123
```

### Review Process

1. **Automated Checks** - CI runs tests and linting
2. **Code Review** - Maintainers review code
3. **Feedback** - Address any comments or requested changes
4. **Approval** - Once approved, your PR will be merged

### After Merge

- Your PR will be merged into `main`
- Delete your feature branch
- Contribution will be credited in release notes

## Areas for Contribution

### High Priority

- **Framework Integrations** - Add support for more frameworks (Semantic Kernel, Haystack, etc.)
- **Performance Optimizations** - Improve ingestion throughput and query performance
- **Bug Fixes** - Address open issues
- **Documentation** - Improve guides and examples

### Features We'd Love

- Advanced replay executors for specific frameworks
- Enhanced failure classification rules
- Real-time streaming updates in UI
- Export/import functionality
- Multi-tenancy support
- Authentication and authorization

### Good First Issues

Look for issues labeled `good first issue` on GitHub. These are:
- Well-defined and scoped
- Good for getting familiar with the codebase
- Typically require less context

## Project Structure

Understanding the codebase:

```
AgentTrace/
├── packages/
│   ├── core/           # Shared models and utilities
│   ├── ingestion/      # OTLP ingestion service
│   ├── analysis/       # Analysis engine and API
│   ├── replay/         # Replay debugging engine
│   └── sdk/python/     # Python SDK
├── web/                # React frontend
├── docs/               # Documentation
├── migrations/         # Database migrations
├── tests/              # Integration tests
└── deploy/             # Deployment configs
```

## Questions and Support

### Communication Channels

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Questions and general discussion
- **Pull Requests** - Code contributions

### Getting Help

If you need help:

1. Check the [documentation](docs/)
2. Search existing GitHub issues
3. Ask in GitHub Discussions
4. Tag maintainers in your PR if stuck

### Maintainers

Current maintainers:
- @jimmybentley

## Recognition

Contributors are recognized in:
- Release notes
- Contributors section in README
- GitHub contributor graph

Thank you for contributing to AgentTrace! Your efforts help make debugging multi-agent systems better for everyone.

## License

By contributing to AgentTrace, you agree that your contributions will be licensed under the MIT License.
