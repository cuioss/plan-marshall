---
name: python-core
description: "Use when writing, reviewing, or refactoring Python 3.10+ code — covers type annotations, data structures, error handling, resource management, async patterns, naming conventions, and imports. Activate for any Python production code task. Also use when working with pathlib, dataclass, pydantic, match statements, or structural pattern matching, or when hardening untrusted input (secure subprocess, deserialization, eval, and SQL injection sinks). Carries the Python production-code review rules a code review cites."
user-invocable: false
mode: knowledge
---

# Python Core Standards

**REFERENCE MODE**: This skill provides reference material for Python 3.10+ development. Load standards on-demand based on current task. Do not load all sections at once.

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

## When to Use This Skill

Activate when:
- **Writing Python production code** — type annotations, data structures, class and function design
- **Reviewing Python code** — checking adherence to PEP 8 and modern Python patterns
- **Refactoring Python code** — modernizing type hints, improving error handling, adopting pathlib
- **Handling resources** — file I/O, context managers, pathlib operations
- **Writing async code** — asyncio patterns, concurrency, rate limiting
- **Naming decisions** — module, class, function, variable, and constant naming conventions

## Available References

**File**: `standards/python-core.md` (771 lines)

Load progressively by section based on current task. **Never load the entire file at once.**

| Section | Load When |
|---------|-----------|
| Type Annotations | Writing or reviewing type hints, choosing between built-in generics and `collections.abc` |
| Data Structures | Choosing between `dataclass`, `attrs`, `pydantic`, `NamedTuple` |
| Error Handling | Writing try/except blocks, custom exceptions, validation patterns |
| Resource Management | File I/O, context managers, custom resource cleanup |
| Path Handling | File path operations, `pathlib.Path` usage, path security |
| Security / injection | Validating untrusted input, running subprocesses, deserializing external data, building SQL (`subprocess`/`shlex`, `pickle`/`yaml.safe_load`, `eval`/`ast.literal_eval`, DB-API placeholders) |
| Async Programming | `asyncio` patterns, concurrency with `gather()`, rate limiting |
| Structural Pattern Matching | `match` statements, destructuring, class patterns, guard clauses |
| Modern Features (3.11-3.13) | Exception groups, `@override`, `itertools.batched()` |
| Functions and Classes | Function design, class composition, mutable defaults |
| Naming Conventions | Module/class/function/variable naming styles |
| Imports | Import organization, grouping, and rules |
| Docstrings | Google-style format for functions, classes, and modules |
| Comprehensions and Generators | List/dict comprehensions, generator expressions |
| String Handling | F-strings, multi-line strings, string building |

**Load Command**:
```text
Read standards/python-core.md
```

## Quick Reference

| Topic | Rule |
|-------|------|
| Type hints | Built-in generics (`list[str]`), union syntax (`X \| None`), `collections.abc` for parameters |
| Data structures | `dataclass` (default), `attrs` (performance), `pydantic` (API boundaries) |
| Error handling | Specific exceptions only, minimal try scope, chain with `from` |
| Resources | Always context managers; `pathlib.Path` for all file/path operations |
| Security / injection | No `shell=True`/argv lists; `yaml.safe_load` not `yaml.load`; `ast.literal_eval` not `eval`; DB-API placeholders not f-strings |
| Pattern matching | `match`/`case` for structural destructuring; `if/elif` for simple comparisons |
| Async | `asyncio.run()` entry point, `gather()` for concurrency, `Semaphore` for rate limiting |
| Naming | `lower_with_under` (functions/modules), `CapWords` (classes), `CAPS_WITH_UNDER` (constants) |
| Docstrings | Google style with Args/Returns/Raises sections |
| Imports | Three groups (stdlib, third-party, local), sorted alphabetically |

## Related Skills

- `pm-dev-python:pytest-testing` - Testing standards with pytest
- `pm-plugin-development:plugin-script-architecture` - Standards for marketplace plugin scripts

## Review Rules

The review rules of the python domain for production code — what a code review looks for in a changed Python module. The block follows the harvestable block contract — see [`review-rubric.md` § 10 "Harvestable review-rule blocks"](../../../plan-marshall/skills/phase-6-finalize/standards/review-rubric.md) for its rules, which are not restated here.

- A local assignment, loop variable, or `with … as` / `except … as` target that rebinds a name the module imports at top level, so later code in the same scope that expects the imported object reads the rebound value instead.
- A function whose default argument is a mutable object (a list, dict or set) that the body mutates, so state written on one call is visible to every later call.
- A bare `except:` or an `except Exception:` that neither re-raises nor narrows to the failure it handles, so an unexpected error — a programming bug included — is swallowed and the function carries on with partial state.
- A value that can be `None` (an `X | None` annotation, a `dict.get`, a `re.match` result) dereferenced without a `None` check, so an absent entry raises `AttributeError` or `TypeError` on an ordinary input.
- A file, socket or process opened outside a `with` block or `try`/`finally`, so an exception before the close leaks the handle or leaves a partially written file behind.
- A `match` statement over a closed set of variants with no `case _` arm, so a value outside the handled cases falls through and the function returns `None` as if it had handled it.
- An `asyncio.create_task` result that is neither awaited nor kept, so the task can be garbage-collected mid-run and its exception is never observed.
