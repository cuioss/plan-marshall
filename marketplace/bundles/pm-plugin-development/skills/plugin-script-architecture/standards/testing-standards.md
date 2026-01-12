# Testing Standards

Standards for testing Python scripts in the marketplace. Tests use **Python stdlib only** - no external frameworks required.

## Quick Start

```bash
python3 test/run-tests.py                                          # all tests
python3 test/run-tests.py test/planning/                           # directory
python3 test/run-tests.py test/planning/plan-files/test_parse_plan.py  # single file
```

## Directory Structure

```
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

### Option 2: Class-Based Style (For complex scripts with setup/teardown)

```python
#!/usr/bin/env python3
"""Tests for manage-adr.py script."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import ScriptTestCase

class TestManageAdr(ScriptTestCase):
    """Test ADR management script."""

    bundle = 'pm-documents'
    skill = 'adr-management'
    script = 'manage-adr.py'

    def test_create_adr(self):
        """Test creating a new ADR."""
        result = self.run_script('create', '--title', 'Use PostgreSQL')
        self.assert_success(result)
        data = result.json()
        self.assertEqual(data['number'], 1)
        self.assertIn('001-Use_PostgreSQL.adoc', data['path'])

    def test_list_empty(self):
        """Test listing ADRs when none exist."""
        result = self.run_script('list')
        self.assert_success(result)
        data = result.json()
        self.assertEqual(data['count'], 0)

if __name__ == '__main__':
    unittest.main()
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
"""Tests for manage-config.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner, get_script_path, PlanTestContext

SCRIPT_PATH = get_script_path('pm-workflow', 'manage-config', 'manage-config.py')

# Alias for backward compatibility (optional)
TestContext = PlanTestContext

def test_create_config():
    """Test creating a config file."""
    with PlanTestContext(plan_id='test-config') as ctx:
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-config',
            '--domain', 'java'
        )
        assert result.success, f"Script failed: {result.stderr}"
        # ctx.fixture_dir - base test directory
        # ctx.plan_dir - path to plans/{plan_id}
```

### How It Works

1. **Via `test/run-tests.py`**: Creates `.plan/temp/test-fixture/{timestamp}` once, passes to all tests via `TEST_FIXTURE_DIR` and `PLAN_BASE_DIR` env vars, cleans up after all tests complete.

2. **Standalone execution**: Each `PlanTestContext` creates its own timestamped directory in `.plan/temp/test-fixture/standalone-{timestamp}` and cleans up when exiting the context.

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

```
test/pm-plugin-development/plugin-diagnose/fixtures/
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

1. **`test/run-tests.py`** builds PYTHONPATH from all `marketplace/bundles/*/skills/*/scripts/` directories
2. **`test/conftest.py`** adds the same directories to `sys.path` on import
3. Scripts can use direct imports without sys.path manipulation

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
from run_config import ext_defaults_get
from extension_base import PROFILE_PATTERNS
```

### Key Points

- **No sys.path manipulation needed** for cross-skill imports
- The test runner sets PYTHONPATH environment variable for subprocess tests
- conftest.py adds paths to sys.path for direct imports
- IDE warnings about unresolved imports are expected (PYTHONPATH is set at runtime)

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

### `conftest.ScriptTestCase`

Base class for unittest-style tests with automatic cleanup.

**Class attributes**:
- `bundle` - Bundle name
- `skill` - Skill name
- `script` - Script filename

**Methods**:
- `run_script(*args)` - Run the configured script
- `run_script_with_file(content, *args)` - Create temp file and run
- `assert_success(result)` - Assert returncode == 0
- `assert_failure(result)` - Assert returncode != 0

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
with PlanTestContext(plan_id='my-plan') as ctx:
    result = run_script(SCRIPT_PATH, '--plan-id', 'my-plan')
    assert result.success
```

### `conftest.get_test_fixture_dir()`

Get the test fixture directory. Uses `TEST_FIXTURE_DIR` env var when run via `test/run-tests.py`, otherwise creates a standalone directory.

## Test Modularization (400+ Lines)

**Rule**: Test files exceeding 400 lines MUST be modularized by command module while keeping integration tests.

### Module Structure

Split large test files into focused modules:

| Module | Purpose |
|--------|---------|
| `test_helpers.py` | Shared fixtures and helper functions (no test functions) |
| `test_cmd_{noun}.py` | Detailed tests for each command module |
| `test_{script}.py` | Happy-path integration tests only |

### Example Structure

```
test/{bundle}/{skill}/
  test_helpers.py              # Shared fixtures
  test_cmd_init.py             # init command variants/corners
  test_cmd_skill_domains.py    # skill-domains variants/corners
  test_cmd_modules.py          # modules variants/corners
  test_{script}.py             # Happy-path integration only
```

### test_helpers.py Pattern

```python
#!/usr/bin/env python3
"""Shared test fixtures for {script} tests."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path

SCRIPT_PATH = get_script_path('{bundle}', '{skill}', '{script}.py')

def create_fixture(fixture_dir: Path, config: dict = None) -> Path:
    """Create test fixture in fixture directory."""
    # Fixture creation logic
    pass
```

### test_cmd_{noun}.py Pattern

```python
#!/usr/bin/env python3
"""Tests for {noun} command in {script}.

Tests {noun} command variants and edge cases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner, PlanTestContext
from test_helpers import SCRIPT_PATH, create_fixture

def test_{noun}_happy_path():
    """Test {noun} basic operation."""
    with PlanTestContext() as ctx:
        create_fixture(ctx.fixture_dir)
        result = run_script(SCRIPT_PATH, '{noun}', 'verb')
        assert result.success

def test_{noun}_edge_case():
    """Test {noun} edge case."""
    # Edge case testing
    pass

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_{noun}_happy_path,
        test_{noun}_edge_case,
    ])
    sys.exit(runner.run())
```

### Main Test File Pattern (Integration Only)

```python
#!/usr/bin/env python3
"""Integration tests for {script}.py script.

Happy-path tests verifying the monolithic CLI API.
Detailed variant and corner case tests are in:
- test_cmd_{noun1}.py
- test_cmd_{noun2}.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner, PlanTestContext
from test_helpers import SCRIPT_PATH, create_fixture

def test_{noun1}_happy_path():
    """Test {noun1} basic operation."""
    # One simple happy-path test per command
    pass

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_{noun1}_happy_path,
        test_{noun2}_happy_path,
    ])
    sys.exit(runner.run())
```

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

## Test Quality Checklist

Before marking tests as complete:

- [ ] Test file exists: `test/{bundle}/{skill}/test_{script}.py`
- [ ] Happy path test with assertions
- [ ] Missing input test with assertions
- [ ] Invalid input test with assertions
- [ ] Edge case tests with assertions
- [ ] All tests have at least one `assert` statement
- [ ] Fixtures are in `fixtures/` directory
- [ ] Tests pass: `python3 test/run-tests.py test/{bundle}/{skill}/`
- [ ] Test files >400 lines are modularized by command
