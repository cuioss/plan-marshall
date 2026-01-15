# Python Implementation Standards

Standards for implementing Python scripts in the marketplace.

## Shebang and Encoding

All Python scripts MUST start with:

```python
#!/usr/bin/env python3
"""Brief description of what the script does."""
```

## Stdlib-Only Requirement

**CRITICAL**: Scripts MUST use only Python standard library (no pip dependencies).

See `references/stdlib-modules.md` for the complete list of allowed modules.

**Rationale**: Scripts must work on any system with Python 3 installed, without requiring package installation.

## Subcommand Pattern

Scripts MUST follow the `{noun}.py {verb}` pattern using argparse subparsers.

**Required Pattern**:
```python
#!/usr/bin/env python3
"""Manage configuration files for plans."""

import argparse
import json
import sys

def cmd_get(args):
    """Handle 'get' subcommand."""
    # Implementation
    pass

def cmd_set(args):
    """Handle 'set' subcommand."""
    # Implementation
    pass

def cmd_list(args):
    """Handle 'list' subcommand."""
    # Implementation
    pass

def main():
    parser = argparse.ArgumentParser(
        description="Manage configuration files for plans"
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # get subcommand
    get_parser = subparsers.add_parser('get', help='Get a config value')
    get_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_parser.add_argument('--key', required=True, help='Configuration key')
    get_parser.set_defaults(func=cmd_get)

    # set subcommand
    set_parser = subparsers.add_parser('set', help='Set a config value')
    set_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_parser.add_argument('--key', required=True, help='Configuration key')
    set_parser.add_argument('--value', required=True, help='Value to set')
    set_parser.set_defaults(func=cmd_set)

    # list subcommand
    list_parser = subparsers.add_parser('list', help='List all config values')
    list_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    list_parser.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
```

**Naming Convention**:
- Script name is a noun: `manage-config.py`, `manage-files.py`, `analyze.py`
- Subcommands are verbs: `get`, `set`, `list`, `add`, `remove`, `validate`

**Anti-patterns** (DO NOT use):
- `get-config.py` - verb-noun pattern
- `add-file.py` - verb-noun pattern
- Scripts without subcommand support

## Help Output Requirements

**CRITICAL**: All scripts MUST support `--help` flag via argparse.

Argparse provides automatic help generation. Ensure:
- Parser has a description
- All arguments have help text
- Subparsers have individual help

**Test**:
```bash
python3 .plan/execute-script.py {bundle}:{skill} --help
python3 .plan/execute-script.py {bundle}:{skill} {subcommand} --help
```

## Error Handling

### Input Validation

```python
def cmd_get(args):
    """Handle 'get' subcommand."""
    plan_path = Path(f".plan/plans/{args.plan_id}")

    # Validate plan exists
    if not plan_path.exists():
        print(json.dumps({"error": f"Plan not found: {args.plan_id}"}), file=sys.stderr)
        sys.exit(1)

    # Validate key format
    if not re.match(r'^[a-z][a-z0-9_]*$', args.key):
        print(json.dumps({"error": f"Invalid key format: {args.key}"}), file=sys.stderr)
        sys.exit(1)

    # ... implementation
```

### Error Messages

**Format**: Clear, actionable error messages

**Good Examples**:
```python
{"error": "Plan not found: my-plan"}
{"error": "Invalid key format. Expected: lowercase with underscores, got: MyKey"}
{"error": "Config file parsing failed at line 42: unexpected character"}
```

**Bad Examples**:
```python
{"error": "Error"}  # Too vague
{"error": "Failed"}  # No context
{"error": "1"}  # Not descriptive
```

## Simple YAML Parsing

**DO NOT** use PyYAML. Use custom parsing for simple frontmatter:

```python
def parse_simple_yaml(content: str) -> dict:
    """Parse simple YAML frontmatter (key:value pairs only).

    Handles:
    - key: value pairs
    - Quoted values
    - Simple arrays (single line)
    """
    result = {}
    for line in content.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            result[key] = value
    return result
```

**Key Insight**: Simple YAML parsing is sufficient for frontmatter - full YAML library is not needed.

## Handler Dictionary Pattern

For scripts with multiple operations:

```python
FIX_HANDLERS = {
    "missing_frontmatter": handle_missing_frontmatter,
    "invalid_yaml": handle_invalid_yaml,
    "unused_tools": handle_unused_tools,
}

def apply_fix(fix_type: str, file_path: str, **kwargs) -> dict:
    handler = FIX_HANDLERS.get(fix_type)
    if not handler:
        return {"error": f"Unknown fix type: {fix_type}"}
    return handler(file_path, **kwargs)
```

## Backup Before Modify Pattern

Always backup files before modification:

```python
import shutil
from pathlib import Path

def apply_fix_with_backup(file_path: str, fix_func) -> dict:
    backup_path = Path(file_path).with_suffix('.bak')
    shutil.copy2(file_path, backup_path)
    try:
        result = fix_func(file_path)
        backup_path.unlink()  # Remove backup on success
        return result
    except Exception as e:
        shutil.copy2(backup_path, file_path)  # Restore on failure
        backup_path.unlink()
        return {"error": str(e)}
```

## Executable Permissions

Scripts MUST have executable permissions:

```bash
chmod +x scripts/script-name.py
```

**Verify**:
```bash
ls -l scripts/
# Should show: -rwxr-xr-x (executable flag set)
```

## Script Modularization (400+ Lines)

**Rule**: Scripts exceeding 400 lines MUST be modularized by subcommand while keeping a monolithic API.

### Module Structure

Split large scripts into focused modules:

| Module | Purpose |
|--------|---------|
| `{script}.py` | Main entry point with argparse parser and dispatch only |
| `config_core.py` | Shared utilities (load/save, error handling, output) |
| `config_defaults.py` | Constants and default configurations |
| `cmd_{noun}.py` | Command handlers for each noun/subcommand group |

### Import Pattern

Command modules import shared utilities from config_core:

```python
from config_core import (
    EXIT_ERROR,
    MarshalNotInitializedError,
    require_initialized,
    load_config,
    save_config,
    error_exit,
    success_exit,
)
```

Main script imports command handlers:

```python
from cmd_skill_domains import cmd_skill_domains, cmd_resolve_domain_skills
from cmd_modules import cmd_modules
from cmd_build_systems import cmd_build_systems
```

### Module Size Guidelines

| Module Type | Target Lines |
|-------------|-------------|
| Main script (parser + dispatch) | <250 |
| Command handler modules | <300 |
| Shared utilities | <150 |
| Constants/defaults | <100 |

### When to Modularize

Apply modularization when:
- Script exceeds 400 lines
- Script has 4+ subcommand groups
- Command handlers are largely independent

### Benefits

- Each module is focused and self-contained
- Easier to understand, test, and maintain
- API remains monolithic (same CLI interface)
- Parallel development possible

## Unit Consistency

**Rule**: Use consistent units throughout a script. For time-related values, prefer **seconds** (human-readable, standard in Python).

### Anti-pattern: Mixed Units

```python
# BAD: Mixing milliseconds and seconds
timeout_ms = timeout_get(...)  # Returns milliseconds
duration = int(time.time() - start)  # Seconds (time.time() returns seconds)
config["duration_ms"] = duration * 1000  # Convert back to ms

output = {
    "duration_ms": duration_ms,
    "timeout_used_ms": timeout_ms,
    "elapsed": duration  # Seconds - inconsistent!
}
```

### Correct Pattern: Consistent Units

```python
# GOOD: Everything in seconds
timeout = timeout_get(...)  # Returns seconds
duration = int(time.time() - start)  # Seconds
config["timeout_seconds"] = timeout

output = {
    "duration_seconds": duration,
    "timeout_seconds": timeout
}
```

### Unit Naming Convention

Include the unit in variable and key names:

| Unit | Suffix | Example |
|------|--------|---------|
| Seconds | `_seconds` | `timeout_seconds`, `duration_seconds` |
| Milliseconds | `_ms` | `latency_ms` (only if ms is required) |
| Bytes | `_bytes` | `file_size_bytes` |
| Count | `_count` | `error_count`, `retry_count` |

### Why Seconds for Time

- Python's `time.time()` returns seconds
- Human-readable (120 seconds vs 120000 milliseconds)
- Standard in Unix/POSIX conventions
- Easier mental math during debugging

## API Functions Pattern

**Rule**: Scripts SHOULD expose pure API functions separate from CLI wrappers, enabling direct import by other scripts.

### Two-Layer Design

```python
# Layer 1: Pure API functions (no argparse dependency)
def timeout_get(command_key: str, default: int, project_dir: str = '.') -> int:
    """Get timeout for a command. Returns default if not persisted.

    Args:
        command_key: The command identifier
        default: Default timeout in seconds
        project_dir: Project directory containing run config

    Returns:
        Timeout in seconds
    """
    config = load_run_config(get_config_path(project_dir))
    persisted = config.get("commands", {}).get(command_key, {}).get("timeout_seconds")
    return default if persisted is None else int(persisted * SAFETY_MARGIN)


def timeout_set(command_key: str, duration: int, project_dir: str = '.') -> None:
    """Persist timeout for a command using weighted average."""
    # Implementation...


# Layer 2: CLI wrappers that call API functions
def cmd_timeout_get(args):
    """CLI wrapper for timeout_get."""
    result = timeout_get(args.command_key, args.default, args.project_dir or '.')
    print(json.dumps({"timeout_seconds": result}))


def cmd_timeout_set(args):
    """CLI wrapper for timeout_set."""
    timeout_set(args.command_key, args.duration, args.project_dir or '.')
    print(json.dumps({"status": "ok"}))
```

### API Function Requirements

- **No `args` parameter**: Accept explicit typed parameters
- **Type hints**: All parameters and return types annotated
- **Docstrings**: Describe purpose, arguments, and return value
- **No stdout**: Return values; let callers decide on output
- **Raise exceptions**: Don't call `sys.exit()` in API functions

### CLI Wrapper Requirements

- **Thin**: Only parse args and call API function
- **Handle output**: Print JSON results to stdout
- **Handle errors**: Catch exceptions and format error output
- **Call sys.exit**: Only in wrappers, not in API functions

### Benefits

- **Importable**: Other scripts can call `timeout_get()` directly
- **Testable**: Unit tests call API functions without argparse
- **Reusable**: Same logic available via CLI and programmatic API

## File Naming for Import Compatibility

**Rule**: Python files that may be imported as modules MUST use underscores, not hyphens.

### Why This Matters

Python module names cannot contain hyphens. A file named `run-config.py` cannot be imported:

```python
# FAILS - Python syntax error
from run-config import timeout_get
```

### Naming Convention

| Component | Naming | Example |
|-----------|--------|---------|
| Directory names | MAY use hyphens | `run-config/`, `json-file-operations/` |
| Python files for import | MUST use underscores | `run_config.py`, `config_core.py` |
| Entry-point-only scripts | MAY use hyphens | `doctor-marketplace.py` (if never imported) |

### Recommended: Always Use Underscores

For consistency and future-proofing, prefer underscores for all Python files:

```
scripts/
  run_config.py       # ✓ Can be imported
  config_core.py      # ✓ Can be imported
  cmd_timeout.py      # ✓ Can be imported
```

### Anti-pattern

```
scripts/
  run-config.py       # ✗ Cannot be imported
  manage-files.py     # ✗ Cannot be imported
```

## Direct Python Imports vs Subprocess

**Rule**: When script A needs functionality from script B, and both are Python, use direct imports instead of subprocess calls.

> **See also**: `standards/cross-skill-integration.md` for complete executor integration patterns including PYTHONPATH setup, standard APIs, and type ignore conventions.

### Anti-pattern: Subprocess to Python Script

```python
# BAD: Subprocess call to Python script
result = subprocess.run([
    "python3", ".plan/execute-script.py",
    "plan-marshall:manage-run-config:run_config",
    "timeout", "get", "--command-key", command_key
], capture_output=True, text=True)
# Then parse JSON output...
timeout = json.loads(result.stdout)["timeout_seconds"]
```

### Correct Pattern: Direct Import

```python
# GOOD: Direct import and function call
from run_config import timeout_get

timeout = timeout_get(command_key, default=300)
```

### When to Use Each Approach

| Scenario | Use |
|----------|-----|
| Calling another Python script in marketplace | Direct import |
| Calling external commands (git, gh, mvn) | Subprocess |
| Calling system utilities (ls, cat, grep) | Subprocess |
| Cross-language calls (Python to Bash) | Subprocess |

### Benefits of Direct Import

- **No parsing**: Return native Python types, not JSON strings
- **Type safety**: Function signatures with type hints
- **Performance**: No subprocess overhead
- **Testability**: Can mock functions in unit tests
- **Error handling**: Catch exceptions directly

## Environment Variables for Path Configuration

**Rule**: Scripts MUST use environment variables for configurable paths, not hardcoded values.

### PLAN_DIR_NAME Pattern

The executor exports `PLAN_DIR_NAME` to child scripts. Use it for path construction:

```python
import os
from pathlib import Path

# Get plan directory name from environment (with fallback for standalone)
_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

# Use in path construction
DATA_DIR = Path(_PLAN_DIR_NAME) / "project-architecture"
CONFIG_PATH = Path(project_dir) / _PLAN_DIR_NAME / "run-configuration.json"
```

### Why Use Environment Variables

- **Test isolation**: Tests can override paths without modifying code
- **Parallel execution**: Multiple projects can run simultaneously without interference
- **Single source of truth**: Configuration centralized in executor generation

### Pattern Requirements

| Requirement | Pattern |
|-------------|---------|
| Always provide fallback | `os.environ.get('PLAN_DIR_NAME', '.plan')` |
| Use underscore prefix | `_PLAN_DIR_NAME` (module-level constant) |
| Construct paths from variable | `Path(_PLAN_DIR_NAME) / "subdir"` |

### Anti-patterns

```python
# BAD: Hardcoded path
DATA_DIR = Path(".plan/project-architecture")

# BAD: No fallback
_PLAN_DIR_NAME = os.environ['PLAN_DIR_NAME']  # Raises KeyError if not set

# BAD: Using full path when only name needed
_PLAN_BASE = os.environ.get('PLAN_BASE_DIR')  # Wrong variable for path construction
```

## Script Quality Checklist

Before marking script as "quality approved":

- [ ] Shebang: `#!/usr/bin/env python3`
- [ ] Stdlib-only (no pip dependencies)
- [ ] Subcommand pattern: `{noun}.py {verb}`
- [ ] Argparse with subparsers
- [ ] All arguments have help text
- [ ] Error handling with clear messages
- [ ] Exit codes (0 for success, 1 for error)
- [ ] Executable permissions set
- [ ] Test file exists and passes
- [ ] Scripts >400 lines are modularized by subcommand
- [ ] Uses `PLAN_DIR_NAME` env var for path construction (not hardcoded `.plan`)
