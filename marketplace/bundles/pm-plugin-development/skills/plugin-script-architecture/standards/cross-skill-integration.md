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
# FAIL WRONG - sys.path manipulation
import sys
from pathlib import Path

LOGGING_DIR = Path(__file__).parent.parent.parent.parent.parent / 'plan-marshall' / 'skills' / 'logging' / 'scripts'
sys.path.insert(0, str(LOGGING_DIR))

from plan_logging import log_entry
```

### Correct Pattern

```python
# PASS CORRECT - direct import (executor sets PYTHONPATH)
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
log_entry('work', 'EXAMPLE-PLAN-id', 'INFO', '[ARTIFACT] Created deliverable')

# Log errors
log_entry('script', 'global', 'ERROR', '[MY-COMPONENT] Failed to process')
```

**Parameters**:

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `log_type` | str | `'script'`, `'work'` | Determines output file |
| `plan_id` | str | kebab-case or `'global'` | Plan identifier |
| `level` | str | `'INFO'`, `'WARNING'`, `'ERROR'` | Log level |
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
plan_dir = base_path('plans', 'EXAMPLE-PLAN')

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
# FAIL WRONG - subprocess call to Python script
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
# PASS CORRECT - direct import and function call
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
# FAIL WRONG - silent failure
try:
    result = parse_toon(content)
except Exception:
    pass  # Silent failure - debugging nightmare
```

### Correct Patterns

```python
# PASS CORRECT - let errors propagate
result = parse_toon(content)

# PASS CORRECT - catch specific exceptions with recovery logic
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
# FAIL WRONG - unnecessary parameters
subprocess.run(cmd, capture_output=True, cwd=project_root, timeout=5)

# PASS CORRECT - minimal (when not reading output)
subprocess.run(cmd, timeout=5)

# PASS CORRECT - when reading output
result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
value = result.stdout.strip()

# PASS CORRECT - with automatic error checking
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
├── _tasks_crud.py       # Internal - CRUD command handlers
├── _tasks_query.py      # Internal - query command handlers
└── _cmd_step.py         # Internal - step command handlers
```

### Naming Convention

Internal modules use the `{skill}_{role}.py` convention to ensure unique filenames across sibling skills. For example, `_tasks_crud.py` and `_tasks_query.py` in manage-tasks vs `_references_crud.py` in manage-references. This prevents module cache collisions in tests.

### Import Pattern

Entry point imports from internal modules:

```python
# manage-tasks.py (entry point)
from _manage_tasks_shared import parse_task_file, format_task_file
from _tasks_crud import cmd_add, cmd_remove
from _tasks_query import cmd_list, cmd_get
```

Internal modules import from each other or from cross-skill APIs:

```python
# _tasks_crud.py (internal module)
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

## Script invocation in documentation

When a skill, workflow, agent, or command document invokes a marketplace script — i.e. spells out a `python3 .plan/execute-script.py {bundle}:{skill}:{script} …` call in its prose — the written call MUST be correct against the script's live argparse surface at the moment it is read. Paraphrased, invented, or stale invocations are the structural cause of the argparse-rejection (exit code 2) recurrence: a call that reads naturally in workflow prose but does not match the declared subcommands, sub-verbs, or required flags fails silently, bypasses the script body, and corrupts downstream behaviour.

This standard codifies three normative rules. They attack the failure at *authoring time* (when the call is written), not at runtime.

### Rule 1 — exact inline call

When a document writes a script invocation inline, the call MUST match the script's argparse declaration exactly: a registered top-level subcommand, a registered sub-verb when the subcommand declares nested subparsers, only declared long flags, and every flag the resolved leaf parser marks `required=True`. Never synthesize a verb that names the goal rather than quoting a declared subcommand, never place a verb-scoped flag at the top level, and never substitute a plausible-but-wrong flag name. When in doubt, verify against `python3 .plan/execute-script.py {notation} --help` and `python3 .plan/execute-script.py {notation} {subcommand} --help` before writing the call.

### Rule 2 — xref, don't restate

Prefer an explicit cross-reference to the owning skill's `## Canonical invocations` section over restating the call inline. An inline restatement is a copy that drifts the moment the script's argparse surface changes; a named xref ("see `{skill}` Canonical invocations → `{subcommand}`") always resolves to the current source-of-truth. Restate inline only when the surrounding prose genuinely needs the literal command in place (e.g. a step-by-step workflow the reader executes verbatim); even then, the inline call MUST satisfy Rule 1.

### Rule 3 — every script-bearing skill publishes a Canonical-invocations section

Every skill that registers an argparse CLI entry-point invoked via 3-part `bundle:skill:script` executor notation MUST publish a `## Canonical invocations` section in its `SKILL.md`. This section is the single source-of-truth that Rule-2 xrefs resolve against. A skill that registers multiple entry-point scripts publishes one section grouping per registered notation triple.

### Canonical-invocations section contract

The section's structure is fixed so the consuming analyzer can locate and validate it deterministically:

- **Heading**: exactly `## Canonical invocations`. The consuming analyzer matches the heading with the regex `^##\s+Canonical\s+invocations\s*$` (case-insensitive) — any other spelling (e.g. `## Canonical Invocation`, `## Canonical commands`) is not recognized and leaves the skill flagged as missing the section.
- **Per-subcommand subsections**: one `### {subcommand}` heading per registered top-level argparse subcommand (for a script with no subcommands, document the single root-parser invocation).
- **Canonical-call block**: each `### {subcommand}` subsection carries a fenced ` ```bash ` block showing the canonical call — the full `python3 .plan/execute-script.py {notation} {subcommand} …` form with every required flag, mirroring the live argparse declaration exactly. Optional flags are shown in `[brackets]`; mutually-exclusive groups are shown as `(--a | --b)`.
- **Authoring source**: author each block by reading the script's argparse declaration (subcommands, sub-verbs, `required=True` flags) — verify against `{notation} --help`, never paraphrase.
- **No transitionary prose**: describe the current argparse surface only — no changelog, no "renamed from", no dated update notes.

The reference model is [`manage-files/SKILL.md`](../../../../plan-marshall/skills/manage-files/SKILL.md) § "Canonical invocations" — its layout (one `### {subcommand}` heading per subcommand, each with a `bash` canonical-call block, mutually-exclusive groups rendered as `(--a | --b …)`) is the pattern every script-bearing skill follows.

### Enforcing analyzer and rule IDs

The plugin-doctor analyzer [`_analyze_manage_invocation.py`](../../plugin-doctor/scripts/_analyze_manage_invocation.py) is the consuming static-analysis surface that enforces this contract at edit time. It implements two rule IDs:

- **`manage-invocation-invalid`** — validates each inline invocation (Rule 1) against the script's AST-extracted argparse tree, emitting a finding for an unregistered subcommand, an unregistered sub-verb, an undeclared flag, or a missing required flag.
- **`missing-canonical-block`** — emitted when a script-bearing `SKILL.md` lacks the `## Canonical invocations` section (Rule 3).

Both rules are pure static analysis (AST + regex, no subprocess, no target-script import) and run under `quality-gate`, so a documented call that drifts from the live surface — or a script-bearing skill that omits its Canonical-invocations section — is caught before it ships.

## Integration Rules

Before publishing a script:

- No `sys.path` manipulation for cross-skill imports
- Direct imports instead of subprocess CLI calls (where possible)
- Uses `plan_logging.log_entry()` for logging
- Uses standard APIs (`file_ops`, `toon_parser`, `run_config`) where applicable
- No bare `except: pass` blocks
- Subprocess calls use minimal parameters
- Entry point scripts follow naming convention (`script.py`)
- Internal modules use underscore prefix (`_module.py`)
- IDE import warnings suppressed with `# type: ignore[import-not-found]`
- Tests use conftest import pattern (one sys.path insert only)
- Documented script invocations follow the explicit-call-or-xref rules above; script-bearing skills publish a `## Canonical invocations` section
