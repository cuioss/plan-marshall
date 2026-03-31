---
name: python-best-practices
description: Modern Python development patterns and best practices
user-invocable: false
---

# Python Best Practices

Modern Python development patterns for Python 3.10+ based on PEP 8, Google Python Style Guide, and current community standards.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for Python development tasks.

**Prohibited actions:**
- Do not use `typing.List`, `typing.Dict`, or other deprecated generic aliases; use built-in generics
- Do not use bare `except:` or broad `except Exception:` without re-raising
- Do not use string concatenation for file paths; use `pathlib.Path`
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- All code must target Python 3.10+ and use modern union syntax (`X | Y`)
- Type hints required on all public function signatures
- Google-style docstrings required on all public functions
- Context managers required for all resource management

## Purpose

- Establish consistent, readable Python code
- Apply modern type hints effectively
- Use appropriate patterns for data structures
- Handle errors and resources properly
- Write maintainable async code
- Write reliable, isolated tests with pytest

## When to Reference This Skill

Reference when:
- Writing new Python code
- Reviewing code for standards compliance
- Choosing between data structure approaches
- Implementing error handling or resource management
- Working with async/await patterns
- Writing or reviewing pytest tests

## Focused Skills

This skill serves as entry point. Load the focused skill matching your current task:

| Skill | When to Load |
|-------|-------------|
| `pm-dev-python:python-core` | Writing production code — types, data structures, error handling, naming, imports |
| `pm-dev-python:pytest-testing` | Writing or reviewing tests — fixtures, isolation, mocking, assertions |

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
| Testing | AAA pattern, `tmp_path` isolation, `monkeypatch` for state, `conftest.py` for shared fixtures |

## Related Skills

- `pm-plugin-development:plugin-script-architecture` - Standards for marketplace plugin scripts (stdlib-only, argparse subcommands, TOON output, cross-skill imports via executor). For scripts inside `marketplace/bundles/`, load that skill instead

## Key Principles

1. **Readability counts** - Code is read more often than written
2. **Explicit is better than implicit** - Clear intent over cleverness
3. **Errors should never pass silently** - Handle or propagate explicitly
4. **Flat is better than nested** - Limit nesting depth
5. **Practicality beats purity** - Standards serve code, not vice versa
