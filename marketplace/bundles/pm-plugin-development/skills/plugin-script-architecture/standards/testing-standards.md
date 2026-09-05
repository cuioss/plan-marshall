# Testing Standards

Standards for testing Python scripts in the marketplace. Tests use **Python stdlib only** - no external frameworks required.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `pyproject_build` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Quick Start

Run the suite through the canonical build command (pytest under the hood), never
by executing a test file as a script:

```bash
# All tests
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests"

# A single bundle
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests plan-marshall"
```

## Directory Structure

```text
test/
  conftest.py                    # Shared infrastructure (import this)

  {bundle-name}/                 # Matches marketplace bundle
    {skill-name}/                # Matches skill directory
      test_{script-name}.py      # Tests for scripts/{script-name}.py
      fixtures/                  # Optional fixture files
        sample-input.md
```

## Writing Tests

### Option 1: Functional Style (Recommended for simple scripts)

```python
#!/usr/bin/env python3
"""Tests for parse-plan.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, create_temp_file, TestRunner, get_script_path

# Get script path
SCRIPT_PATH = get_script_path('planning', 'plan-files', 'parse-plan.py')

# Test fixtures (inline for simple cases)
BASIC_PLAN = """# Task Plan: Test Feature

**Current Phase**: init
**Current Task**: task-1
"""

def test_parse_basic_plan():
    """Test parsing a basic plan."""
    temp_file = create_temp_file(BASIC_PLAN)
    try:
        result = run_script(SCRIPT_PATH, str(temp_file))
        assert result.success, f"Script failed: {result.stderr}"
        data = result.json()
        assert data['title'] == 'Test Feature'
        assert data['current_phase'] == 'init'
    finally:
        temp_file.unlink()

def test_file_not_found():
    """Test error handling for missing file."""
    result = run_script(SCRIPT_PATH, '/nonexistent/path.md')
    assert not result.success
    data = result.json_or_error()
    assert 'error' in data

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_parse_basic_plan,
        test_file_not_found,
    ])
    sys.exit(runner.run())
```

### Option 2: Pytest Class Style (For grouping related tests)

```python
#!/usr/bin/env python3
"""Tests for manage-adr.py script."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-adr', 'manage-adr.py')


class TestManageAdr:
    """Test ADR management script."""

    def test_create_adr(self, tmp_path):
        """Test creating a new ADR."""
        result = run_script(SCRIPT_PATH, 'create', '--title', 'Use PostgreSQL', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.json()
        assert data['number'] == 1
        assert '001-Use_PostgreSQL.adoc' in data['path']

    def test_list_empty(self, tmp_path):
        """Test listing ADRs when none exist."""
        result = run_script(SCRIPT_PATH, 'list', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.json()
        assert data['count'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

## Required Test Categories

**CRITICAL**: Every script MUST have tests for these categories:

### 1. Happy Path
Normal successful execution.

```python
def test_basic_success():
    """Happy path - normal operation."""
    result = run_script(SCRIPT_PATH, '--mode', 'structured')
    assert result.success
    data = result.json()
    assert data['status'] == 'success'
```

### 2. Missing Input
Required file/argument not provided.

```python
def test_file_not_found():
    """Missing input - file doesn't exist."""
    result = run_script(SCRIPT_PATH, '/nonexistent/path.md')
    assert not result.success
    data = result.json_or_error()
    assert 'error' in data
```

### 3. Invalid Input
Malformed input data.

```python
def test_invalid_format():
    """Invalid input - malformed content."""
    temp_file = create_temp_file("not valid yaml: {{{")
    try:
        result = run_script(SCRIPT_PATH, str(temp_file))
        assert not result.success
    finally:
        temp_file.unlink()
```

### 4. Edge Cases
Empty input, boundary values.

```python
def test_empty_input():
    """Edge case - empty file."""
    temp_file = create_temp_file("")
    try:
        result = run_script(SCRIPT_PATH, str(temp_file))
        # Verify appropriate handling
        assert result.success or 'error' in result.json_or_error()
    finally:
        temp_file.unlink()
```

## Assertion Requirements

**CRITICAL**: Every test function MUST contain at least one `assert` statement.

Tests without assertions provide no verification value.

### Common Assertion Patterns

```python
# Verify exit code 0
assert result.success

# Explicit exit code check
assert result.returncode == 0

# Verify output content
assert 'expected' in result.stdout

# Verify parsed data
assert data['field'] == expected_value

# Verify expected failure
assert not result.success
```

### Anti-patterns to Avoid

```python
# BAD: Test only calls function without assertions
def test_no_assertion():
    result = run_script(SCRIPT_PATH, 'arg')
    result.json()  # No assertion!

# BAD: Assigns to variable but never asserts
def test_assigns_only():
    result = run_script(SCRIPT_PATH, 'arg')
    data = result.json()
    status = data['status']  # No assertion on status!

# BAD: Checks parsing without verifying content
def test_parses_only():
    result = run_script(SCRIPT_PATH, 'arg')
    result.json()  # Just checks it parses, not content!
```

## Plan Test Context

For scripts that use `PLAN_BASE_DIR` (plan management scripts), use `PlanTestContext`:

```python
#!/usr/bin/env python3
"""Tests for manage-references.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner, get_script_path, PlanTestContext

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')

# Alias for backward compatibility (optional)
TestContext = PlanTestContext

def test_create_references():
    """Test creating a references file."""
    with PlanTestContext(plan_id='test-references') as ctx:
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-references',
            '--domain', 'java'
        )
        assert result.success, f"Script failed: {result.stderr}"
        # ctx.fixture_dir - base test directory
        # ctx.plan_dir - path to plans/{plan_id}
```

### How It Works

Each `PlanTestContext` creates its own timestamped directory in
`.plan/temp/test-fixture/standalone-{timestamp}` and cleans up when exiting the
context. (A `TEST_FIXTURE_DIR` env var, when set, overrides the location; nothing
in the suite sets it by default.)

### PlanTestContext Attributes

| Attribute | Description |
|-----------|-------------|
| `fixture_dir` | Base test fixture directory (`.plan/temp/test-fixture/...`) |
| `plan_id` | The plan identifier passed to constructor |
| `plan_dir` | Path to `{fixture_dir}/plans/{plan_id}` |

### Extending PlanTestContext

For custom test requirements:

```python
class TestContextWithMarshal(PlanTestContext):
    """Extended context with marshal.json path."""

    def __init__(self):
        super().__init__(plan_id='marshal-test')

    @property
    def marshal_path(self) -> Path:
        return self.fixture_dir / 'marshal.json'
```

## Test Fixtures

**Location**: `test/{bundle}/{skill}/fixtures/`

**Purpose**: Test input files and expected outputs

```text
test/pm-plugin-development/plugin-doctor/fixtures/
└── analyze-markdown-file/
    ├── valid-agent.md
    ├── bloated-command.md
    ├── missing-frontmatter.md
    └── invalid-yaml.md
```

### Using Fixtures

```python
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / 'fixtures'

def test_with_fixture_file():
    fixture_path = FIXTURES_DIR / 'sample-maven-success.log'
    result = run_script(SCRIPT_PATH, '--log', str(fixture_path))
    assert result.success
```

## Cross-Skill Imports in Tests

The test infrastructure mirrors the executor's PYTHONPATH setup, enabling direct imports from any skill's scripts directory.

> **See also**: `standards/cross-skill-integration.md` for complete details on PYTHONPATH setup, import patterns, and type ignore conventions.

### How It Works

1. **`test/conftest.py`** builds PYTHONPATH from all `marketplace/bundles/*/skills/*/scripts/` directories and adds them to `sys.path` on import
2. Scripts can use direct imports without sys.path manipulation

### Using Cross-Skill Imports

```python
#!/usr/bin/env python3
"""Tests that use cross-skill imports."""

import sys
from pathlib import Path

# Import shared infrastructure (triggers PYTHONPATH setup)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner

# Direct imports from other skills work automatically
from plan_logging import log_entry
from _config_core import ext_defaults_get
from extension_base import PROFILE_PATTERNS
```

### Key Points

- **No sys.path manipulation needed** for cross-skill imports
- The test runner sets PYTHONPATH environment variable for subprocess tests
- conftest.py adds paths to sys.path for direct imports
- IDE warnings about unresolved imports are expected (PYTHONPATH is set at runtime)

### Internal Module Loading (importlib Pattern)

Internal script modules are loaded via `importlib.util.spec_from_file_location` with unique synthetic module names to avoid Python's module cache issues when tests span multiple skills:

```python
import importlib.util
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / '{bundle}' / 'skills' / '{skill}' / 'scripts'
)

def _load_module(name, filename):
    """Load a module by file path with a unique synthetic name."""
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# Use unique prefixes for synthetic module names
_crud = _load_module('_tasks_cmd_crud', '_tasks_crud.py')
_query = _load_module('_tasks_cmd_query', '_tasks_query.py')
```

**When to use**: For internal modules (underscore-prefixed) that are loaded from a specific skill's scripts directory. The `{skill}_{role}.py` naming convention ensures unique filenames across sibling skills.

## Naming Conventions

| Item | Convention | Example |
|------|------------|---------|
| Test file | `test_{script_name}.py` | `test_parse_plan.py` |
| Test function | `test_{what_it_tests}` | `test_parse_basic_plan` |
| Test class | `Test{ScriptName}` | `TestParseConfig` |
| Fixture file | `sample-{description}.{ext}` | `sample-maven-success.log` |

## API Reference

### `conftest.run_script(script_path, *args, input_data=None, cwd=None, timeout=30)`

Run a Python script and capture output.

**Returns**: `ScriptResult` with:
- `.returncode` - Exit code
- `.stdout` - Standard output
- `.stderr` - Standard error
- `.success` - True if returncode == 0
- `.json()` - Parse stdout as JSON
- `.json_or_error()` - Parse stdout or stderr as JSON

### `conftest.get_script_path(bundle, skill, script)`

Get absolute path to a marketplace script.

**Example**:
```python
path = get_script_path('planning', 'plan-files', 'parse-plan.py')
# Returns: /path/to/marketplace/bundles/planning/skills/plan-files/scripts/parse-plan.py
```

### `conftest.create_temp_file(content, suffix='.md', dir=None)`

Create a temporary file with content. Caller must delete.

### `conftest.TestRunner`

Simple test runner for functional-style tests.

```python
runner = TestRunner()
runner.add_tests([test_a, test_b, test_c])
sys.exit(runner.run())
```

### `conftest.PlanTestContext`

Context manager for tests needing `PLAN_BASE_DIR`.

**Constructor**:
- `plan_id` - Plan identifier (default: 'test-plan')

**Attributes**:
- `fixture_dir` - Base test directory (`.plan/temp/test-fixture/...`)
- `plan_id` - The plan identifier
- `plan_dir` - Path to `{fixture_dir}/plans/{plan_id}`

**Example**:
```python
with PlanTestContext(plan_id='EXAMPLE-PLAN') as ctx:
    result = run_script(SCRIPT_PATH, '--plan-id', 'EXAMPLE-PLAN')
    assert result.success
```

### `conftest.get_test_fixture_dir()`

Get the test fixture directory. Honours a `TEST_FIXTURE_DIR` env var when one is set, otherwise creates a standalone directory under `.plan/temp/test-fixture/`.

## Test Modularization (400+ Lines)

**Rule**: Test files exceeding 400 lines MUST be modularized by command module while keeping integration tests.

### Module Structure

Split large test files into focused modules:

| Module | Purpose |
|--------|---------|
| `_{domain}_fixtures.py` | Shared fixtures and helper functions (no test functions) |
| `test_cmd_{noun}.py` | Detailed tests for each command module |
| `test_{script}.py` | Happy-path integration tests only |

**A helper module MUST NOT be named `test_*.py`.** pytest collects any module matching its
`python_files` pattern, so a helper under that name is imported, collects nothing, and is invisible in
the run — a silent no-op rather than a loud failure. A whole-tree guard
(`test/test_shared_harness.py`) fails the build on any collected module that declares zero tests, so a
helper named `test_helpers.py` breaks the build.

The name is `_{domain}_fixtures.py`: underscore-prefixed so it is not collected, and domain-prefixed
because helper modules are imported by bare name and their basenames must therefore be unique
tree-wide. `{domain}` is the skill or subject the fixtures serve — the manage-config suite's helpers
live in `_manage_config_fixtures.py`. Never a nested `conftest.py`, and never a bare `_fixtures.py`
or `_helpers.py`.

### Example Structure

```text
test/{bundle}/{skill}/
  _{domain}_fixtures.py        # Shared fixtures
  test_cmd_init.py             # init command variants/corners
  test_cmd_skill_domains.py    # skill-domains variants/corners
  test_cmd_modules.py          # modules variants/corners
  test_{script}.py             # Happy-path integration only
```

### Module Patterns (summary)

- **`_{domain}_fixtures.py`** — imports conftest helpers (`get_script_path`), exposes a module-level `SCRIPT_PATH` constant, and defines `create_fixture(fixture_dir, config)` and any other shared helpers. No test functions.
- **`test_cmd_{noun}.py`** — imports `run_script`, `TestRunner`, `PlanTestContext` from conftest and `SCRIPT_PATH`, `create_fixture` from `_{domain}_fixtures`. Contains detailed `test_{noun}_happy_path`, `test_{noun}_edge_case`, etc. The `__main__` block wires them into a `TestRunner`.
- **Main test file** (`test_{script}.py`) — same imports, but contains only one happy-path test per command and acts as the monolithic CLI API contract test. Detailed variant and corner cases live in the per-command modules.

### Module Size Guidelines

| Module Type | Target Lines |
|-------------|-------------|
| Main test file (integration only) | <250 |
| Command test modules | <400 |
| Shared helpers | <150 |

### When to Modularize Tests

Apply modularization when:
- Test file exceeds 400 lines
- Script has modular structure (cmd_*.py files)
- Tests cover 4+ subcommand groups

### Benefits

- Parallel structure to script modules (cmd_{noun}.py → test_cmd_{noun}.py)
- Easier to maintain (changes to a command only need editing corresponding test file)
- Main test file serves as API contract test
- Individual module tests cover all variants and corner cases

## Test Quality Rules

Before marking tests as complete:

- Test file exists: `test/{bundle}/{skill}/test_{script}.py`
- Happy path test with assertions
- Missing input test with assertions
- Invalid input test with assertions
- Edge case tests with assertions
- All tests have at least one `assert` statement
- Fixtures are in `fixtures/` directory
- Tests pass: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests {bundle}"`
- Test files >400 lines are modularized by command
