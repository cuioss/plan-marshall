# Python Core Patterns

Comprehensive Python best practices for Python 3.10+ based on PEP 8, Google Python Style Guide, and modern community standards.

---

## Type Annotations

### Modern Syntax (Python 3.10+)

```python
# Built-in generics - prefer over typing module equivalents
items: list[str]
mapping: dict[str, int]
optional: str | None

# Union syntax with |
def fetch(url: str) -> dict | None:
    ...

# Use float instead of int | float (float accepts int)
def calculate(value: float) -> float:
    ...
```

### Abstract Types for Parameters

Use `collections.abc` for function parameters to accept any compatible type:

```python
from collections.abc import Mapping, Sequence, Iterable

# Accept any mapping, return concrete dict
def transform(data: Mapping[str, int]) -> dict[str, str]:
    return {k: str(v) for k, v in data.items()}

# Accept any iterable
def process_all(items: Iterable[str]) -> list[str]:
    return [item.upper() for item in items]
```

### TypedDict for Structured Data

```python
from typing import TypedDict, NotRequired

class UserData(TypedDict):
    name: str
    email: str
    age: NotRequired[int]  # Optional field

def create_user(data: UserData) -> None:
    ...
```

### Type Aliases

```python
# Python 3.12+ type statement
type Vector = list[float]
type Matrix = list[Vector]

# Pre-3.12 alternative
from typing import TypeAlias
Vector: TypeAlias = list[float]
```

---

## Data Structures

### Choosing the Right Tool

| Use Case | Choice | Reason |
|----------|--------|--------|
| Simple data container | `dataclass` | Standard library, no dependencies |
| Performance-critical | `attrs` with `slots=True` | Faster, more features |
| API boundaries | `pydantic` | Validation, JSON serialization |
| Immutable config | `dataclass(frozen=True)` | Prevents modification |

### Dataclasses

```python
from dataclasses import dataclass, field

@dataclass(slots=True)
class User:
    name: str
    email: str
    tags: list[str] = field(default_factory=list)

# Immutable version
@dataclass(frozen=True, slots=True)
class Config:
    host: str
    port: int = 8080
```

### Named Tuples

For simple immutable records:

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float

    def distance_from_origin(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5
```

---

## Error Handling

### Principles

1. **Catch specific exceptions** - Never bare `except:` or broad `except Exception:`
2. **Minimize try scope** - Only wrap code that may raise the expected exception
3. **Chain exceptions** - Use `from` to preserve context
4. **Fail fast** - Validate early and raise meaningful errors

### Patterns

```python
# Specific exceptions with minimal scope
try:
    config = parse_config(path)
except FileNotFoundError:
    config = default_config()
except json.JSONDecodeError as e:
    raise ConfigError(f"Invalid JSON in {path}") from e

# Early validation
def process_file(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.suffix == ".json":
        raise ValueError(f"Expected JSON file, got: {path.suffix}")
    # Main logic after validation
    ...
```

### Anti-Patterns to Avoid

```python
# BAD: Bare except catches everything including KeyboardInterrupt
try:
    result = risky_operation()
except:
    pass

# BAD: Catching Exception hides bugs
try:
    result = operation()
except Exception:
    result = default

# BAD: Large try block obscures error source
try:
    data = fetch_data()
    processed = transform(data)
    result = save(processed)
except ValueError:
    ...  # Which function raised it?
```

---

## Resource Management

### Context Managers

Always use context managers for resources that need cleanup:

```python
# File operations
with open(path, "r", encoding="utf-8") as f:
    data = f.read()

# Multiple resources
with open(input_path) as src, open(output_path, "w") as dst:
    dst.write(process(src.read()))

# Database connections, network sockets, locks
with connection.cursor() as cursor:
    cursor.execute(query)
```

### pathlib for File Operations

```python
from pathlib import Path

# Simple read/write (handles open/close automatically)
content = Path("data.txt").read_text(encoding="utf-8")
Path("output.txt").write_text(result, encoding="utf-8")

# Binary files
data = Path("image.png").read_bytes()
Path("copy.png").write_bytes(data)
```

### Custom Context Managers

```python
from contextlib import contextmanager

@contextmanager
def temporary_directory():
    import tempfile
    import shutil
    path = Path(tempfile.mkdtemp())
    try:
        yield path
    finally:
        shutil.rmtree(path)
```

---

## Path Handling

### Use pathlib, Not Strings

```python
from pathlib import Path

# Path construction with / operator
config_path = Path("data") / "config" / "settings.json"

# Cross-platform - works on Windows and Unix
project_root = Path.cwd()
home = Path.home()

# Never string concatenation
# BAD: path = "data" + "/" + "file.txt"
# GOOD: path = Path("data") / "file.txt"
```

### Common Operations

```python
path = Path("data/config/settings.json")

# Components
path.name        # "settings.json"
path.stem        # "settings"
path.suffix      # ".json"
path.parent      # Path("data/config")
path.parts       # ("data", "config", "settings.json")

# Checks
path.exists()
path.is_file()
path.is_dir()

# Traversal
for file in path.parent.iterdir():
    if file.suffix == ".json":
        process(file)

# Glob patterns
for py_file in Path("src").rglob("*.py"):
    analyze(py_file)
```

### Security

```python
# Validate user input paths to prevent traversal attacks
user_path = Path(user_input)
safe_base = Path("/data/uploads")

# Check path doesn't escape base directory
if not user_path.resolve().is_relative_to(safe_base):
    raise ValueError("Invalid path")
```

---

## Async Programming

### Entry Point

```python
import asyncio

async def main():
    result = await fetch_data()
    return result

# Always use asyncio.run() as entry point
if __name__ == "__main__":
    asyncio.run(main())
```

### Concurrent Execution

```python
# Sequential (slow) - each await blocks
result1 = await fetch("url1")
result2 = await fetch("url2")

# Concurrent (fast) - both run simultaneously
results = await asyncio.gather(
    fetch("url1"),
    fetch("url2"),
)

# With tasks for more control
task1 = asyncio.create_task(fetch("url1"))
task2 = asyncio.create_task(fetch("url2"))
result1 = await task1
result2 = await task2
```

### Rate Limiting with Semaphores

```python
async def fetch_all(urls: list[str], max_concurrent: int = 10):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(url: str):
        async with semaphore:
            return await fetch(url)

    return await asyncio.gather(*[fetch_one(url) for url in urls])
```

### CPU-Bound Work

Offload CPU-intensive work to avoid blocking the event loop:

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

async def process_images(paths: list[Path]):
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        results = await asyncio.gather(*[
            loop.run_in_executor(pool, process_image, path)
            for path in paths
        ])
    return results
```

---

## Functions and Classes

### Function Design

```python
# Keep functions focused and under ~40 lines
def calculate_total(items: list[Item], tax_rate: float = 0.0) -> float:
    """Calculate total price including tax."""
    subtotal = sum(item.price * item.quantity for item in items)
    return subtotal * (1 + tax_rate)

# Use early returns to reduce nesting
def get_user(user_id: int) -> User | None:
    if user_id <= 0:
        return None
    user = database.find(user_id)
    if not user.is_active:
        return None
    return user
```

### Avoid Mutable Default Arguments

```python
# BAD: Mutable default is shared across calls
def append_item(item, items=[]):
    items.append(item)
    return items

# GOOD: Use None and create inside function
def append_item(item, items: list | None = None):
    if items is None:
        items = []
    items.append(item)
    return items

# BEST: Use dataclass field factory for class attributes
from dataclasses import dataclass, field

@dataclass
class Container:
    items: list[str] = field(default_factory=list)
```

### Class Design

```python
# Prefer composition over inheritance
class UserService:
    def __init__(self, repository: UserRepository, cache: Cache):
        self._repository = repository
        self._cache = cache

# Use properties only for trivial computed values
class Rectangle:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    @property
    def area(self) -> float:
        return self.width * self.height

# Avoid staticmethod - use module-level functions instead
# BAD: Rectangle.validate(data)
# GOOD: validate_rectangle(data)
```

---

## Naming Conventions

| Type | Style | Example |
|------|-------|---------|
| Module | `lower_with_under` | `user_service.py` |
| Package | `lower_with_under` | `my_package/` |
| Class | `CapWords` | `UserService` |
| Exception | `CapWords` + Error | `ValidationError` |
| Function | `lower_with_under` | `get_user_by_id()` |
| Method | `lower_with_under` | `calculate_total()` |
| Variable | `lower_with_under` | `user_count` |
| Constant | `CAPS_WITH_UNDER` | `MAX_RETRIES` |
| Type Variable | `CapWords` | `T`, `KeyType` |
| Internal | `_leading_under` | `_internal_helper` |

### Naming Guidelines

- Avoid abbreviations unfamiliar outside your project
- Single-character names only for iterators (`i`, `j`) or math notation
- Boolean variables: `is_valid`, `has_permission`, `can_edit`
- Collections: plural nouns (`users`, `items`)

---

## Imports

### Organization

Three groups separated by blank lines, each sorted alphabetically:

```python
# 1. Standard library
import json
import sys
from pathlib import Path
from typing import TypedDict

# 2. Third-party packages
import requests
from pydantic import BaseModel

# 3. Local application imports
from myapp.models import User
from myapp.utils import format_date
```

### Rules

```python
# Import modules, not individual items (with exceptions)
import os
result = os.path.exists(path)

# Acceptable: typing, collections.abc, dataclasses
from typing import TypedDict, Literal
from collections.abc import Mapping
from dataclasses import dataclass, field

# Never wildcard imports
# BAD: from module import *
```

---

## Docstrings

### Google Style Format

```python
def fetch_users(
    filters: dict[str, str],
    limit: int = 100,
    include_inactive: bool = False,
) -> list[User]:
    """Fetch users matching the given filters.

    Retrieves users from the database that match all provided
    filter criteria. Results are ordered by creation date.

    Args:
        filters: Key-value pairs for filtering (e.g., {"role": "admin"}).
        limit: Maximum number of users to return.
        include_inactive: Whether to include deactivated accounts.

    Returns:
        List of User objects matching the criteria, ordered by
        creation date descending. Empty list if no matches.

    Raises:
        DatabaseError: If the database connection fails.
        ValueError: If filters contains invalid keys.

    Example:
        >>> users = fetch_users({"department": "engineering"}, limit=10)
        >>> len(users)
        10
    """
```

### Module and Class Docstrings

```python
"""User management utilities.

This module provides functions for user CRUD operations
and authentication helpers.
"""

class UserService:
    """Service for user-related business logic.

    Handles user creation, updates, and authentication.
    All methods are transaction-safe.

    Attributes:
        repository: The underlying data access layer.
        cache: Optional cache for read operations.
    """
```

---

## Comprehensions and Generators

### List Comprehensions

```python
# Simple transformations - prefer comprehension
squares = [x ** 2 for x in range(10)]
names = [user.name for user in users if user.is_active]

# Complex logic - use regular loop
results = []
for item in items:
    if item.is_valid():
        processed = transform(item)
        if processed.meets_criteria():
            results.append(processed)
```

### Generator Expressions

Use for large datasets to save memory:

```python
# Generator - processes one item at a time
total = sum(order.amount for order in orders)

# Avoid creating intermediate lists
# BAD: sum([x ** 2 for x in range(1000000)])
# GOOD: sum(x ** 2 for x in range(1000000))
```

### Dictionary Comprehensions

```python
# Create dict from iterable
user_map = {user.id: user for user in users}

# Filter and transform
active_emails = {
    user.id: user.email
    for user in users
    if user.is_active
}
```

---

## String Handling

### F-Strings (Preferred)

```python
name = "Alice"
count = 42

# Simple interpolation
message = f"Hello, {name}! You have {count} messages."

# Expressions
message = f"Total: {price * quantity:.2f}"

# Debugging (Python 3.8+)
print(f"{variable=}")  # Prints: variable=value
```

### Multi-line Strings

```python
# Use triple quotes
query = """
    SELECT *
    FROM users
    WHERE active = true
"""

# Or parentheses for implicit concatenation
message = (
    f"User {user.name} has been "
    f"active for {user.days_active} days"
)
```

### String Building

```python
# For loops - use join, not concatenation
# BAD: result = ""; for s in items: result += s
# GOOD:
result = "".join(items)
result = ", ".join(str(x) for x in numbers)

# For complex building, use list and join
parts = []
for item in items:
    if item.is_valid():
        parts.append(format_item(item))
result = "\n".join(parts)
```

---

## Testing

### Test Function Names

Describe the scenario and expected outcome:

```python
def test_user_creation_with_valid_data_succeeds():
    ...

def test_user_creation_with_invalid_email_raises_validation_error():
    ...

def test_fetch_users_returns_empty_list_when_no_matches():
    ...
```

### Fixtures

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    """Create a temporary config file."""
    config = tmp_path / "config.json"
    config.write_text('{"debug": true}')
    return config

def test_load_config(sample_config: Path):
    result = load_config(sample_config)
    assert result["debug"] is True
```

### Assertions

```python
# Be specific
assert result == expected
assert len(items) == 3
assert "error" in message.lower()

# For exceptions
with pytest.raises(ValueError, match="invalid email"):
    create_user(invalid_data)
```

---

## References

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Python Typing Best Practices](https://typing.python.org/en/latest/reference/best_practices.html)
- [Real Python Best Practices](https://realpython.com/tutorials/best-practices/)
