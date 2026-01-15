# Script Organisation Standard

Naming conventions and organisation patterns for Python scripts in marketplace bundles.

---

## Overview

Scripts in marketplace bundles follow a two-tier visibility model:

1. **CLI Entry Points**: Public scripts exposed via the executor
2. **Internal Modules**: Private implementation modules not exposed externally

```
                    SCRIPT VISIBILITY MODEL

    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  External Callers (Claude Code, CLI, Tests)             │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ python3 .plan/execute-script.py                   │  │
    │  │   pm-dev-java:plan-marshall-plugin:maven run ...  │  │
    │  └───────────────────────────────────────────────────┘  │
    │                         │                               │
    │                         ▼                               │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ CLI Entry Point (maven.py)                        │  │
    │  │ - Public interface                                │  │
    │  │ - Argument parsing                                │  │
    │  │ - Subcommand routing                              │  │
    │  └───────────────────────────────────────────────────┘  │
    │                         │                               │
    │                         ▼                               │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ Internal Modules (_maven_execute.py, etc.)        │  │
    │  │ - Implementation details                          │  │
    │  │ - Not exposed via executor                        │  │
    │  │ - Can be tested directly in unit tests            │  │
    │  └───────────────────────────────────────────────────┘  │
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

---

## Naming Conventions

### CLI Entry Points (Public)

- **Pattern**: `<tool>.py` (no underscore prefix)
- **Examples**: `maven.py`, `gradle.py`, `npm.py`
- **Location**: `skills/<skill-name>/scripts/`
- **Purpose**: Single entry point with subcommands

```python
# maven.py - CLI entry point
#!/usr/bin/env python3
"""Maven build operations - run, parse, search markers, check warnings."""

import argparse
from _maven_execute import cmd_run
from _maven_cmd_parse import cmd_parse
# ...

def main():
    parser = argparse.ArgumentParser(...)
    # Subcommand definitions
```

### Internal Modules (Private)

- **Pattern**: `_<tool>_<purpose>.py` (single underscore prefix)
- **Examples**: `_maven_execute.py`, `_maven_cmd_parse.py`, `_npm_parse_eslint.py`
- **Location**: `skills/<skill-name>/scripts/`
- **Purpose**: Implementation modules imported by CLI entry points

```python
# _maven_execute.py - Internal module
#!/usr/bin/env python3
"""Maven build execution (internal module).

This module is imported by maven.py. Do not call directly.
"""
```

---

## Why Underscore Prefix?

The single underscore prefix follows Python community conventions (PEP 8):

1. **Explicit signal**: Indicates "internal implementation detail"
2. **Import protection**: `from module import *` skips underscore-prefixed names
3. **Simple**: No directory restructuring needed
4. **Widely understood**: Matches pip, setuptools, and stdlib patterns

```
                    UNDERSCORE PREFIX SEMANTICS

    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  Python Import Behavior                                 │
    │                                                         │
    │  from package import *                                  │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ Imports:                                          │  │
    │  │   ✓ maven.py         (public)                     │  │
    │  │   ✓ gradle.py        (public)                     │  │
    │  │   ✓ npm.py           (public)                     │  │
    │  │                                                   │  │
    │  │ Skips:                                            │  │
    │  │   ✗ _maven_execute.py      (internal)             │  │
    │  │   ✗ _maven_cmd_parse.py    (internal)             │  │
    │  │   ✗ _npm_parse_eslint.py   (internal)             │  │
    │  └───────────────────────────────────────────────────┘  │
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
skills/<skill-name>/scripts/
├── __init__.py              # Package marker (optional docstring)
├── maven.py                 # CLI entry point (public)
├── gradle.py                # CLI entry point (public)
├── _maven_execute.py        # Internal: build execution
├── _maven_cmd_parse.py      # Internal: log parsing
├── _maven_cmd_discover.py   # Internal: module discovery
├── _gradle_execute.py       # Internal: build execution
├── _gradle_cmd_parse.py     # Internal: log parsing
└── _gradle_cmd_discover.py  # Internal: module discovery
```

---

## Executor Mapping

Only CLI entry points are registered in the executor. Internal modules are never exposed.

```python
# generate-executor.py mapping (simplified)
SCRIPT_MAPPING = {
    "pm-dev-java:plan-marshall-plugin:maven": ".../scripts/maven.py",
    "pm-dev-java:plan-marshall-plugin:gradle": ".../scripts/gradle.py",
    # Internal modules NOT included:
    # NO: "pm-dev-java:plan-marshall-plugin:_maven_execute"
    # NO: "pm-dev-java:plan-marshall-plugin:_maven_cmd_parse"
}
```

---

## Internal Module Naming Patterns

| Pattern | Purpose | Example |
|---------|---------|---------|
| `_<tool>_execute.py` | Build execution logic | `_maven_execute.py` |
| `_<tool>_cmd_<verb>.py` | Subcommand implementation | `_maven_cmd_parse.py` |
| `_<tool>_parse_<type>.py` | Output parser for specific format | `_npm_parse_eslint.py` |

---

## Testing Patterns

### CLI Tests (Public API)

Test the public CLI interface via subprocess:

```python
# test_maven_execute.py
def test_cli_run_help():
    """Test maven.py run --help works."""
    result = subprocess.run(
        ['python3', str(MAVEN_CLI), 'run', '--help'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert '--commandArgs' in result.stdout
```

### Internal Module Tests

Test internal modules by direct import when detailed unit testing is needed:

```python
# test_maven_cmd_parse.py
"""Tests for maven parse functionality (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use maven.py CLI instead.
"""
from _maven_cmd_parse import parse_log

def test_parse_log_success_returns_tuple():
    result = parse_log(log_file)
    assert isinstance(result, tuple)
```

---

## Extension Points

Extensions (e.g., `extension.py`) may import internal discovery modules:

```python
# extension.py
from _maven_cmd_discover import discover_maven_modules
from _gradle_cmd_discover import discover_gradle_modules

class JavaExtension(Extension):
    def discover_modules(self):
        return discover_maven_modules() + discover_gradle_modules()
```

This is acceptable because:
- Extensions are part of the same bundle
- Discovery is an internal extension API, not external CLI
- The underscore signals "internal to this package"

---

## Migration Guide

When converting existing scripts to this pattern:

1. **Identify CLI entry points**: Scripts with `argparse` and `main()` function
2. **Identify internal modules**: Everything else imported by entry points
3. **Rename internal modules**: Add underscore prefix
4. **Update imports**: Both in entry points and cross-module imports
5. **Update tests**: Either convert to CLI testing or update import paths
6. **Move test data**: From `.plan/` to `test/*/fixtures/`

```bash
# Example migration
mv maven_execute.py _maven_execute.py
mv maven_cmd_parse.py _maven_cmd_parse.py

# Update imports in maven.py
# OLD: from maven_execute import cmd_run
# NEW: from _maven_execute import cmd_run
```

---

## References

- [PEP 8 - Naming Conventions](https://peps.python.org/pep-0008/#naming-conventions)
- [Python `_internal` pattern (pip)](https://pip.pypa.io/en/stable/development/architecture/)
