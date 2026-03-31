---
name: python-core
description: "Use when writing, reviewing, or refactoring Python 3.10+ code — covers type annotations, data structures, error handling, resource management, async patterns, naming conventions, and imports. Activate for any Python production code task."
user-invocable: false
---

# Python Core Standards

Core Python development patterns for Python 3.10+ based on PEP 8, Google Python Style Guide, and modern community standards.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for Python development tasks.

**Prohibited actions:**
- Do not use `typing.List`, `typing.Dict`, or other deprecated generic aliases; use built-in generics
- Do not use bare `except:` or broad `except Exception:` without re-raising
- Do not use string concatenation for file paths; use `pathlib.Path`

**Constraints:**
- All code must target Python 3.10+ and use modern union syntax (`X | Y`)
- Type hints required on all public function signatures
- Google-style docstrings required on all public functions
- Context managers required for all resource management

## Standards Documents

| Document | Content |
|----------|---------|
| [python-core.md](standards/python-core.md) | Complete patterns reference — types, data structures, error handling, resources, paths, async, functions, classes, naming, imports, docstrings, comprehensions, strings |

## Quick Reference

| Topic | Rule |
|-------|------|
| Type hints | Built-in generics (`list[str]`), union syntax (`X \| None`), `collections.abc` for parameters |
| Data structures | `dataclass` (default), `attrs` (performance), `pydantic` (API boundaries) |
| Error handling | Specific exceptions only, minimal try scope, chain with `from` |
| Resources | Always context managers; `pathlib.Path` for all file/path operations |
| Async | `asyncio.run()` entry point, `gather()` for concurrency, `Semaphore` for rate limiting |
| Naming | `lower_with_under` (functions/modules), `CapWords` (classes), `CAPS_WITH_UNDER` (constants) |
| Docstrings | Google style with Args/Returns/Raises sections |
| Imports | Three groups (stdlib, third-party, local), sorted alphabetically |

## Related Skills

- `pm-dev-python:pytest-testing` - Testing standards with pytest
- `pm-plugin-development:plugin-script-architecture` - Standards for marketplace plugin scripts
