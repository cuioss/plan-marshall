# Cross-Skill Integration Standards

Standards for scripts that integrate with the executor and import from other skills.

## PYTHONPATH Setup by Executor

The executor (`execute-script.py`) automatically configures PYTHONPATH to include all skill script directories. Scripts do NOT need to manipulate `sys.path` for cross-skill imports.

### How It Works

When a script runs via the executor:

1. Executor builds PYTHONPATH from all `marketplace/bundles/*/skills/*/scripts/` directories
2. Script inherits this PYTHONPATH
3. Direct imports from any skill work automatically

### Implication

Scripts can import from ANY skill's scripts directory without path manipulation:

```python
# These imports work because executor sets PYTHONPATH
from plan_logging import log_entry
from _config_core import ext_defaults_get
from toon_parser import parse_toon, serialize_toon
from file_ops import atomic_write_file, base_path
```

## No sys.path Manipulation

**CRITICAL**: Never manipulate `sys.path` for cross-skill imports.

### Anti-Pattern (DO NOT USE)

```python
# ❌ WRONG - sys.path manipulation
import sys
from pathlib import Path

LOGGING_DIR = Path(__file__).parent.parent.parent.parent.parent / 'plan-marshall' / 'skills' / 'logging' / 'scripts'
sys.path.insert(0, str(LOGGING_DIR))

from plan_logging import log_entry
```

### Correct Pattern

```python
# ✅ CORRECT - direct import (executor sets PYTHONPATH)
from plan_logging import log_entry
```

### Exception

Importing from the SAME skill's scripts directory is acceptable (same directory):

```python
# OK - same skill, same directory
from _helpers import parse_config
from _validators import validate_input
```

## Type Ignore Comments

IDE tools (Pylance, mypy) show "Import could not be resolved" warnings for cross-skill imports because PYTHONPATH is set at runtime, not at development time.

### Handling IDE Warnings

Add `# type: ignore[import-not-found]` to suppress IDE noise:

```python
from plan_logging import log_entry  # type: ignore[import-not-found]
from _config_core import ext_defaults_get  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]
from file_ops import atomic_write_file  # type: ignore[import-not-found]
```

### Why This Is Acceptable

- PYTHONPATH is correctly set at runtime by the executor
- IDE warnings are false positives in this context
- Type ignore comments document that this is intentional

## Standard Cross-Skill APIs

### Logging API: `plan_logging.log_entry()`

Use `plan_logging.log_entry()` for all structured logging needs.

```python
from plan_logging import log_entry  # type: ignore[import-not-found]

# Log to global script log
log_entry('script', 'global', 'INFO', '[MY-COMPONENT] Processing started')

# Log to plan-specific work log
log_entry('work', 'my-plan-id', 'INFO', '[ARTIFACT] Created deliverable')

# Log errors
log_entry('script', 'global', 'ERROR', '[MY-COMPONENT] Failed to process')
```

**Parameters**:

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `log_type` | str | `'script'`, `'work'` | Determines output file |
| `plan_id` | str | kebab-case or `'global'` | Plan identifier |
| `level` | str | `'INFO'`, `'WARN'`, `'ERROR'` | Log level |
| `message` | str | any | Log message (prefix with `[COMPONENT]`) |

**Message Convention**: Prefix messages with `[COMPONENT-NAME]` for easy filtering:
- `[MANAGE-FILES] Created config.toon`
- `[MANAGE-TASKS] Added TASK-003`
- `[GIT-WORKFLOW] Commit formatted`

### Configuration API: `_config_core.ext_defaults_get()`

Use `_config_core.ext_defaults_get()` for accessing extension default values stored in `marshal.json`.

```python
from _config_core import ext_defaults_get  # type: ignore[import-not-found]

# Get extension default value
value = ext_defaults_get('build.maven.profiles.skip', project_dir)
if value:
    skip_list = [s.strip() for s in value.split(",")]
```

**Return Value**: The value directly, or `None` if key not found.

### File Operations API: `file_ops`

Use `file_ops` for atomic file writes and base path resolution.

```python
from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]

# Get path relative to .plan directory
plan_dir = base_path('plans', 'my-plan')

# Write file atomically (prevents partial writes)
atomic_write_file(plan_dir / 'config.toon', content)
```

### TOON Parser API: `toon_parser`

Use `toon_parser` for TOON format parsing and serialization.

```python
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# Parse TOON content
data = parse_toon(file_content)

# Serialize to TOON format
output = serialize_toon({'status': 'success', 'count': 42})
```

## Direct Imports vs Subprocess

**Rule**: When script A needs functionality from script B, and both are Python, use direct imports instead of subprocess calls.

### Anti-Pattern (DO NOT USE)

```python
# ❌ WRONG - subprocess call to Python script
import subprocess
import json

result = subprocess.run([
    "python3", ".plan/execute-script.py",
    "plan-marshall:manage-logging:plan_logging",
    "script", "global", "INFO", "message"
], capture_output=True, text=True, timeout=5)
```

### Correct Pattern

```python
# ✅ CORRECT - direct import and function call
from plan_logging import log_entry  # type: ignore[import-not-found]

log_entry('script', 'global', 'INFO', 'message')
```

### When to Use Each Approach

| Scenario | Use |
|----------|-----|
| Calling another Python script in marketplace | Direct import |
| Calling external commands (git, gh, mvn, npm) | Subprocess |
| Calling system utilities (ls, grep) | Subprocess |
| Cross-language calls (Python to Bash) | Subprocess |

### Benefits of Direct Import

- **No parsing**: Return native Python types, not JSON strings
- **Type safety**: Function signatures with type hints
- **Performance**: No subprocess overhead
- **Testability**: Can mock functions in unit tests
- **Error handling**: Catch exceptions directly

## No Silent Error Handling

**CRITICAL**: Do not swallow exceptions with bare `except: pass`.

### Anti-Pattern (DO NOT USE)

```python
# ❌ WRONG - silent failure
try:
    result = parse_toon(content)
except Exception:
    pass  # Silent failure - debugging nightmare
```

### Correct Patterns

```python
# ✅ CORRECT - let errors propagate
result = parse_toon(content)

# ✅ CORRECT - catch specific exceptions with recovery logic
try:
    status = parse_toon(status_file.read_text())
    result['current_phase'] = status.get('current_phase', 'unknown')
except (ValueError, KeyError, OSError):
    # Specific exceptions with meaningful recovery
    result['has_status'] = True
```

### When Exception Handling Is Acceptable

Only catch exceptions when you have **meaningful recovery logic**:

- Specific exception types (not bare `Exception`)
- Clear fallback behavior
- Documented reasoning

## Subprocess Parameter Guidelines

When subprocess calls ARE appropriate (external commands), use minimal parameters.

### Parameter Usage

| Parameter | When Needed |
|-----------|-------------|
| `capture_output=True` | Only if you need to read `result.stdout` or `result.stderr` |
| `text=True` | Only with `capture_output` when you need string output |
| `cwd=path` | Only if NOT running via executor (rare) |
| `timeout=N` | Always recommended for external calls |
| `check=True` | When you want automatic exception on non-zero exit |

### Examples

```python
# ❌ WRONG - unnecessary parameters
subprocess.run(cmd, capture_output=True, cwd=project_root, timeout=5)

# ✅ CORRECT - minimal (when not reading output)
subprocess.run(cmd, timeout=5)

# ✅ CORRECT - when reading output
result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
value = result.stdout.strip()

# ✅ CORRECT - with automatic error checking
subprocess.run(['git', 'status'], check=True, timeout=30)
```

## Internal Module Naming

Scripts can be split into entry points and internal modules.

### Naming Convention

| Pattern | Purpose | Callable via Executor |
|---------|---------|----------------------|
| `script.py` | CLI entry point | Yes |
| `_script.py` | Internal module | No (imported only) |

### Directory Structure Example

```
skills/my-skill/scripts/
├── manage_tasks.py      # Entry point - registered in executor
├── _manage_tasks_shared.py  # Internal - shared utilities
├── _cmd_crud.py         # Internal - CRUD command handlers
├── _cmd_query.py        # Internal - query command handlers
└── _cmd_step.py         # Internal - step command handlers
```

### Import Pattern

Entry point imports from internal modules:

```python
# manage_tasks.py (entry point)
from _manage_tasks_shared import parse_task_file, format_task_file
from _cmd_crud import cmd_add, cmd_remove
from _cmd_query import cmd_list, cmd_get
```

Internal modules import from each other or from cross-skill APIs:

```python
# _cmd_crud.py (internal module)
from file_ops import atomic_write_file  # type: ignore[import-not-found]
from _manage_tasks_shared import parse_task_file, format_task_file
```

## Test Infrastructure Integration

The test infrastructure mirrors the executor's PYTHONPATH setup.

### How It Works

1. **`test/run-tests.py`**: Builds PYTHONPATH from all script directories, passes to subprocess environment
2. **`test/conftest.py`**: Adds same directories to `sys.path` on import

### Test File Pattern

```python
#!/usr/bin/env python3
"""Tests for my-script.py."""

import sys
from pathlib import Path

# Import shared infrastructure (triggers PYTHONPATH setup)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner, get_script_path

# Get script path
SCRIPT_PATH = get_script_path('my-bundle', 'my-skill', 'my-script.py')

# Direct imports from other skills work automatically
from toon_parser import parse_toon  # type: ignore[import-not-found]

def test_example():
    result = run_script(SCRIPT_PATH, 'subcommand', '--arg', 'value')
    assert result.success
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
```

### Key Points

- **One sys.path insert**: Only for conftest, NOT for cross-skill imports
- **Direct imports work**: After conftest import, cross-skill imports are available
- **IDE warnings expected**: Use `# type: ignore[import-not-found]`

## Integration Checklist

Before publishing a script:

- [ ] No `sys.path` manipulation for cross-skill imports
- [ ] Direct imports instead of subprocess CLI calls (where possible)
- [ ] Uses `plan_logging.log_entry()` for logging
- [ ] Uses standard APIs (`file_ops`, `toon_parser`, `run_config`) where applicable
- [ ] No bare `except: pass` blocks
- [ ] Subprocess calls use minimal parameters
- [ ] Entry point scripts follow naming convention (`script.py`)
- [ ] Internal modules use underscore prefix (`_module.py`)
- [ ] IDE import warnings suppressed with `# type: ignore[import-not-found]`
- [ ] Tests use conftest import pattern (one sys.path insert only)
