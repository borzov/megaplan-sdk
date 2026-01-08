# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Professional asynchronous Python SDK for Megaplan API v3. This library provides type-safe, async/await interface for working with Megaplan CRM entities (tasks, projects, deals, contractors, employees, comments, files).

**Key Technologies:**
- Python 3.11+ with strict typing (mypy strict mode)
- httpx for async HTTP requests
- Pydantic v2 for data validation and models
- pytest with pytest-asyncio for testing

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage (must meet 80% threshold)
pytest --cov=megaplan_sdk --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run specific test function
pytest tests/unit/test_auth.py::test_authenticate

# Run integration tests (requires real Megaplan credentials)
pytest tests/integration/
```

### Type Checking
```bash
# Type check the SDK (strict mode enabled)
mypy megaplan_sdk

# Type check tests (less strict)
mypy tests
```

### Linting and Formatting
```bash
# Check code style
ruff check megaplan_sdk

# Format code
ruff format megaplan_sdk

# Auto-fix issues
ruff check --fix megaplan_sdk
```

### Installation
```bash
# Install for development (editable mode with dev dependencies)
pip install -e ".[dev]"

# Install production version
pip install .
```

## Architecture

### Core Components

1. **MegaplanClient** (`client.py`) - Main entry point
   - Coordinates all resources (tasks, projects, deals, etc.)
   - Manages HTTPClient and AuthManager lifecycle
   - Implements async context manager for resource cleanup
   - Security: Does NOT store passwords after initial authentication

2. **HTTPClient** (`http_client.py`) - Low-level HTTP operations
   - Handles authentication header injection
   - Implements retry logic with exponential backoff for 5xx errors
   - Converts dict params to JSON query string format (Megaplan API requirement)
   - Connection pooling configuration: max 100 connections, 20 keepalive
   - Security: Enforces HTTPS by default (allow_http flag for dev/test only)

3. **AuthManager** (`auth.py`) - OAuth2 token lifecycle
   - Handles username/password authentication
   - Manages token refresh with refresh_token
   - Tracks token expiration with buffer (60s default)
   - Security: Clears password from memory after first use

4. **Resources** (`resources/*.py`) - API endpoint wrappers
   - All inherit from `BaseResource`
   - Pattern: TasksResource, ProjectsResource, DealsResource, ContractorsResource, EmployeesResource, CommentsResource, FileResource
   - Each resource implements CRUD operations and entity-specific methods
   - Generic pagination via `_iterate_generic()` for auto-pagination

5. **Models** (`models/*.py`) - Pydantic data models
   - All inherit from Pydantic BaseModel
   - `BaseEntity` - base for all entities with contentType and id
   - Models use Field(alias="...") for API field name mapping (e.g., contentType → content_type)
   - Config: `populate_by_name=True`, `extra="ignore"` for forward compatibility

### Key Patterns

**API Path Construction:**
```python
# Megaplan API uses: /api/v3/{resource}/{id}
path = self._build_path("api", "v3", "task", str(task_id))
# Results in: /api/v3/task/123
```

**Query Parameters Format:**
Megaplan API expects JSON in query string:
```python
# NOT: /api/v3/task?limit=5&filter=123
# YES: /api/v3/task?{"limit":5,"filter":123}
```
HTTPClient handles this conversion automatically in `_build_url()`.

**Pagination Pattern:**
```python
# List with pagination params
tasks = await client.tasks.list(limit=50, page_after={"contentType": "Task", "id": 100})

# Auto-pagination iterator
async for task in client.tasks.iterate(limit=100):
    process(task)
```

**Generic CRUD in BaseResource:**
- `_get_list()` - fetch and parse list responses
- `_create_entity()` - generic create
- `_get_entity()` - generic get by ID
- `_update_entity()` - generic update
- `_delete_entity()` - generic delete

**Comments Pattern:**
Resources that support comments (tasks, projects, deals, contractors) use:
- `_get_entity_comments()` - generic comment fetching
- `_create_entity_comment()` - generic comment creation

### Exception Hierarchy

All exceptions inherit from `MegaplanError` (`exceptions.py`):
- `AuthenticationError` (401) - Invalid credentials or expired token
- `AuthorizationError` (403) - Insufficient permissions
- `NotFoundError` (404) - Resource not found
- `ValidationError` (422) - Request validation failed, includes `errors` list
- `RateLimitError` (429) - Rate limit exceeded
- `ServerError` (5xx) - Server errors (auto-retry enabled)

## Testing Patterns

### Unit Tests Structure
- Located in `tests/unit/`
- Use `respx` for HTTP mocking
- Test files: `test_{resource}_resource.py` or `test_{module}.py`
- All tests are async: `async def test_function_name():`
- Fixtures in `tests/conftest.py` and `tests/fixtures/`

### Integration Tests
- Located in `tests/integration/`
- Require real Megaplan credentials (use environment variables)
- Run against actual Megaplan API

### Coverage Requirements
- Minimum 80% coverage enforced (`--cov-fail-under=80`)
- Excluded lines: `pragma: no cover`, `if TYPE_CHECKING:`, `__repr__`, NotImplementedError

## Important Notes

### Security Considerations
1. **Password Handling**: Client clears password from memory after first authentication (`_initial_password = None` after use)
2. **HTTPS Enforcement**: HTTPClient rejects HTTP URLs unless `allow_http=True` explicitly set
3. **Token Storage**: AuthManager stores tokens in memory only, not persisted
4. **Logging**: Uses `sanitize_dict()` to prevent logging sensitive data

### API Quirks
1. **JSON in Query String**: Megaplan expects params as `?{"key":"value"}` not `?key=value`
2. **contentType Field**: All entities have contentType (e.g., "Task", "Project", "Deal") for polymorphic references
3. **Pagination**: Uses pageAfter/pageBefore/pageWith with entity references, not offset/limit
4. **Update via POST**: Updates use POST, not PUT/PATCH to `/api/v3/{resource}/{id}`

### Code Style
- Line length: 100 characters
- Quotes: double quotes (enforced by ruff)
- All public functions/classes MUST have docstrings
- Strict typing: all function signatures must have type hints
- Use `str | None` not `Optional[str]` (PEP 604 style)

### Adding New Resources
1. Create model in `megaplan_sdk/models/{name}.py` inheriting from BaseModel
2. Create resource in `megaplan_sdk/resources/{name}.py` inheriting from BaseResource
3. Add to `MegaplanClient.__init__()`: `self.{name} = {Name}Resource(self._http)`
4. Export in `megaplan_sdk/__init__.py` __all__ list
5. Add unit tests in `tests/unit/test_{name}_resource.py`

## Common Development Tasks

### Running Single Test
```bash
pytest tests/unit/test_auth.py::test_authenticate -v
```

### Checking Coverage for Specific Module
```bash
pytest --cov=megaplan_sdk.resources.tasks --cov-report=term-missing tests/unit/test_tasks_resource.py
```

### Type Check Before Commit
```bash
mypy megaplan_sdk && ruff check megaplan_sdk && pytest
```
