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

## Structural Pattern Matching

### Basic Match (Python 3.10+)

```python
def handle_command(command: str) -> str:
    match command.split():
        case ["quit"]:
            return "Goodbye"
        case ["go", direction]:
            return f"Moving {direction}"
        case ["get", item] if item != "sword":
            return f"Picked up {item}"
        case _:
            return "Unknown command"
```

### Matching Data Structures

```python
def process_event(event: dict) -> None:
    match event:
        case {"type": "click", "position": (x, y)}:
            handle_click(x, y)
        case {"type": "keypress", "key": str(key)}:
            handle_key(key)
        case {"type": "error", "code": int(code)} if code >= 500:
            handle_server_error(code)
        case _:
            log_unknown_event(event)
```

### Matching Classes

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

def describe(shape) -> str:
    match shape:
        case Point(x=0, y=0):
            return "Origin"
        case Point(x, y) if x == y:
            return f"On diagonal at {x}"
        case Point(x, y):
            return f"Point({x}, {y})"
```

### When to Use Match vs If/Elif

- **Use `match`**: Destructuring complex data, multiple structural patterns, guard clauses on structure
- **Use `if/elif`**: Simple value comparisons, boolean conditions, fewer than 3 branches

---

## Modern Features (3.11-3.13)

### Exception Groups (3.11+)

```python
# Raise multiple exceptions together
def validate_all(data: dict) -> None:
    errors = []
    if not data.get("name"):
        errors.append(ValueError("name is required"))
    if not data.get("email"):
        errors.append(ValueError("email is required"))
    if errors:
        raise ExceptionGroup("validation failed", errors)

# Catch specific exceptions from a group
try:
    validate_all(data)
except* ValueError as eg:
    for err in eg.exceptions:
        print(f"Validation: {err}")
except* TypeError as eg:
    for err in eg.exceptions:
        print(f"Type error: {err}")
```

### Override Decorator (3.12+)

```python
from typing import override

class Base:
    def get_color(self) -> str:
        return "blue"

class Child(Base):
    @override
    def get_color(self) -> str:  # Verified by type checkers
        return "red"

    @override
    def get_colour(self) -> str:  # Type checker ERROR: no matching base method
        return "red"
```

### Batched Iteration (3.12+)

```python
from itertools import batched

# Process items in chunks
for batch in batched(range(10), 3):
    print(batch)  # (0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)

# Useful for bulk API calls, database inserts
for chunk in batched(records, 100):
    db.insert_many(chunk)
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

Organize into three blank-line-separated, alphabetically sorted groups: standard library, third-party packages, and local application imports. Prefer importing the module and using dotted access (`import os; os.path.exists(path)`); reserve `from ... import name` for explicitly documented helpers (`typing`, `collections.abc`, `dataclasses`). Never use wildcard imports (`from module import *`).

---

## Docstrings

Use Google-style docstrings. Function docstrings start with a one-line summary, followed by a longer description paragraph, then `Args:`, `Returns:`, `Raises:`, and (optionally) `Example:` sections. Document each parameter on its own indented line (`filters: Key-value pairs for filtering`). Always describe the return shape (including the empty-result case) and every exception the function raises.

Module docstrings are one summary line plus a short paragraph describing the module's purpose. Class docstrings include a summary, description, and an `Attributes:` section listing key instance state.

---

## Comprehensions and Generators

Prefer list/dict comprehensions for simple transformations (`[x ** 2 for x in range(10)]`, `{user.id: user for user in users}`) and fall back to a regular loop when the logic branches or mutates state. Use generator expressions (`sum(order.amount for order in orders)`) for large datasets to avoid materializing intermediate lists. Filter-and-transform dict comprehensions read cleanly when the source has an explicit `if` clause.

## String Handling

Use f-strings for interpolation, including format specs (`f"Total: {price * quantity:.2f}"`) and the debug form (`f"{variable=}"`). Use triple-quoted strings for multi-line SQL/text and implicit-concatenation inside parentheses for wrapped logical strings. Build strings with `"".join(items)` or a list-plus-`join` for loops — never with `+=` in a loop.

---

## References

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Python Typing Best Practices](https://typing.python.org/en/latest/reference/best_practices.html)
- [Real Python Best Practices](https://realpython.com/tutorials/best-practices/)
