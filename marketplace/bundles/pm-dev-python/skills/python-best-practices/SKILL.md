---
name: python-best-practices
description: Modern Python development patterns and best practices
user-invocable: false
allowed-tools: Read
---

# Python Best Practices

Modern Python development patterns for Python 3.10+ based on PEP 8, Google Python Style Guide, and current community standards.

## Purpose

- Establish consistent, readable Python code
- Apply modern type hints effectively
- Use appropriate patterns for data structures
- Handle errors and resources properly
- Write maintainable async code

## When to Reference This Skill

Reference when:
- Writing new Python code
- Reviewing code for standards compliance
- Choosing between data structure approaches
- Implementing error handling or resource management
- Working with async/await patterns

## Standards Documents

| Document | Content |
|----------|---------|
| [python-core.md](standards/python-core.md) | Complete patterns reference |

## Quick Reference

### Modern Type Hints (Python 3.10+)

```python
# Use built-in generics (not typing.List, typing.Dict)
def process(items: list[str], config: dict[str, int]) -> bool:
    ...

# Use union syntax with |
def fetch(url: str) -> dict | None:
    ...

# Use collections.abc for abstract types in parameters
from collections.abc import Mapping, Sequence, Iterable

def transform(data: Mapping[str, int]) -> list[str]:
    ...
```

### Data Structures

| Use Case | Choice |
|----------|--------|
| Simple data container | `dataclass` |
| Performance-critical, custom validation | `attrs` |
| API boundaries, JSON serialization | `pydantic` |

```python
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Config:
    host: str
    port: int = 8080
```

### Error Handling

```python
# Specific exceptions, minimal try scope
try:
    result = parse_config(path)
except FileNotFoundError:
    result = default_config()
except ValueError as e:
    raise ConfigError(f"Invalid config: {e}") from e

# Never bare except or catch Exception broadly
# Bad: except:
# Bad: except Exception:
```

### Resource Management

```python
# Always use context managers
from pathlib import Path

# File operations
content = Path("data.txt").read_text(encoding="utf-8")
Path("output.txt").write_text(result, encoding="utf-8")

# For handles that need cleanup
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        process(line)
```

### Path Handling

```python
from pathlib import Path

# Use Path objects, not string concatenation
config_path = Path("data") / "config" / "settings.json"

# Cross-platform by default
if config_path.exists():
    data = config_path.read_text()

# Extract components
name = config_path.stem      # "settings"
ext = config_path.suffix     # ".json"
parent = config_path.parent  # Path("data/config")
```

### Async Patterns

```python
import asyncio

# Entry point
async def main():
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
    )
    return results

asyncio.run(main())

# Controlled concurrency with semaphore
async def fetch_all(urls: list[str], limit: int = 10):
    semaphore = asyncio.Semaphore(limit)

    async def fetch_one(url: str):
        async with semaphore:
            return await fetch_data(url)

    return await asyncio.gather(*[fetch_one(u) for u in urls])
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Module | `lower_with_under` | `user_service.py` |
| Class | `CapWords` | `UserService` |
| Function/Method | `lower_with_under` | `get_user()` |
| Constant | `CAPS_WITH_UNDER` | `MAX_RETRIES` |
| Internal | `_leading_under` | `_internal_helper()` |

### Docstrings (Google Style)

```python
def execute_command(args: str, timeout: int = 300) -> dict:
    """Execute a build command with timeout.

    Args:
        args: Command arguments to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Dictionary with status, exit_code, and output.

    Raises:
        TimeoutError: If command exceeds timeout.
        ValueError: If args is empty.
    """
```

## Key Principles

1. **Readability counts** - Code is read more often than written
2. **Explicit is better than implicit** - Clear intent over cleverness
3. **Errors should never pass silently** - Handle or propagate explicitly
4. **Flat is better than nested** - Limit nesting depth
5. **Practicality beats purity** - Standards serve code, not vice versa
