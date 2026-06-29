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
- Script name is a noun: `manage-references.py`, `manage-files.py`, `analyze.py`
- Subcommands are verbs: `get`, `set`, `list`, `add`, `remove`, `validate`

**Anti-patterns** (DO NOT use):
- `get-config.py` - verb-noun pattern
- `add-file.py` - verb-noun pattern
- Scripts without subcommand support

## Argument Convention

Three rules for argparse arguments:

### 1. Named Flags Only

All arguments MUST use `--kebab-case` flags, never positional arguments.

```python
# CORRECT - named flags
add_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
add_parser.add_argument('--severity', choices=['warning', 'error'], help='Severity level')

# WRONG - positional arguments
add_parser.add_argument('plan_id', help='Plan identifier')
add_parser.add_argument('severity', choices=['warning', 'error'])
```

Use `dest='snake_case'` when flag contains hyphens. Rationale: self-documenting call sites, executor `extract_plan_id()` detection, order-independence.

### 2. kebab-case Naming

Flag names MUST use `--kebab-case` (not `--camelCase` or `--snake_case`).

```python
# CORRECT
add_argument('--command-args', dest='command_args')
add_argument('--file-path', dest='file_path')

# WRONG
add_argument('--commandArgs')
add_argument('--file_path')
```

### 3. Subparser `required=True`

All `add_subparsers()` calls MUST include `required=True` for clear error messages.

```python
# CORRECT
subparsers = parser.add_subparsers(dest='command', required=True)

# WRONG - user gets confusing None error when subcommand omitted
subparsers = parser.add_subparsers(dest='command')
```

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

    # Validate plan exists — return error dict, exit 0 (expected error)
    if not plan_path.exists():
        return {"status": "error", "error": f"Plan not found: {args.plan_id}"}

    # Validate key format — return error dict, exit 0 (expected error)
    if not re.match(r'^[a-z][a-z0-9_]*$', args.key):
        return {"status": "error", "error": f"Invalid key format: {args.key}"}

    # ... implementation
```

### Error Messages

**Format**: Clear, actionable error messages

**Good Examples**:
```python
{"error": "Plan not found: EXAMPLE-PLAN"}
{"error": "Invalid key format. Expected: lowercase with underscores, got: MyKey"}
{"error": "Config file parsing failed at line 42: unexpected character"}
```

**Bad Examples**:
```python
{"error": "Error"}  # Too vague
{"error": "Failed"}  # No context
{"error": "1"}  # Not descriptive
```

## Sibling-Element Invariant Inheritance

**Rule**: When you graft a new code element beside one or more established **sibling elements** that already do the right thing, the new element MUST inherit every invariant its siblings already enforce. Before writing the new element, enumerate its siblings and audit each invariant they apply; then apply the same invariant in the new element. Prefer extracting a shared helper that both the new element and its siblings call, so a future third element inherits the invariant automatically rather than re-deriving it.

A "new element beside established siblings" is any of: a new branch in a multi-branch handler, an alternate return path beside existing return paths, a parallel or CLI-override entry point beside a primary path, a new argparse subcommand alias beside registered subcommands, a new frontmatter-field parser beside existing field parsers, or a new security/control-flow matcher beside existing matchers.

**Why this is the author's responsibility — the in-house gates cannot see it.** Cross-element contract symmetry is invisible to every local gate by construction:

- **module-tests** exercise the happy path of each element independently; they do not assert that two sibling branches return the same field set or apply the same guard.
- **ruff + mypy and plugin-doctor** certify structure and types — that the code parses, is typed, and is structurally well-formed — not that one branch's contract matches its sibling's.
- **the pre-submission self-review surfacer** surfaces deterministic candidates within an element; an asymmetry that is individually well-formed on both sides raises no candidate.

So a divergence between a new element and its sibling passes every local gate clean and surfaces only under adversarial diff review (the PR review bot, or a careful human reviewer reading the diff against the established sibling). The defensive move is twofold: (1) perform the sibling-inheritance audit before you write the element, and (2) add a **cross-element contract test** — one that asserts the new element and its sibling agree on the shared invariant — not merely a happy-path test of the new element in isolation.

### The six invariant facets

Audit each facet that applies to the element you are adding. Each carries a worked before/after.

#### (a) Guard clauses

A new branch must apply the same precondition rejections a sibling already applies before it mutates shared state. A sibling that rejects malformed input before a file rewrite encodes a real invariant; a new branch that rewrites the same file without that check corrupts the file on the input the sibling would have rejected.

```python
# Sibling branch (established): rejects a file lacking an H1 title before rewriting
def cmd_update_title(args):
    text = path.read_text()
    if not text.lstrip().startswith("# "):
        return {"status": "error", "error": "No H1 title to update"}
    # ... safe rewrite

# WRONG — new branch rewrites without inheriting the H1-title guard
def cmd_prepend_section(args):
    text = path.read_text()
    new_text = insert_after_title(text, section)   # corrupts a file with no H1
    path.write_text(new_text)

# RIGHT — new branch inherits the sibling's precondition guard
def cmd_prepend_section(args):
    text = path.read_text()
    if not text.lstrip().startswith("# "):
        return {"status": "error", "error": "No H1 title to anchor the section"}
    path.write_text(insert_after_title(text, section))
```

#### (b) Success-payload field contracts

A new `status: success` return must carry the same documented fields its sibling success branches return, so a caller that handles multiple outcomes uniformly does not break when it hits the new branch. (See [`output-contract.md`](output-contract.md) § "Standard Output Contract" for the success-payload obligation this facet enforces.)

```python
# Sibling success branch returns {status, plan_id, path}
return {"status": "success", "plan_id": pid, "path": str(p)}

# WRONG — new success branch drops fields the sibling guarantees
return {"status": "success", "path": str(p)}   # caller reading plan_id breaks

# RIGHT — new branch returns the full sibling field set
return {"status": "success", "plan_id": pid, "path": str(p)}
```

#### (c) Input-validation range clamps

A parallel or CLI-override entry point must apply the same range/format validation the primary path (e.g. the config-read path) applies, so an override cannot bypass a clamp the primary path enforces.

```python
# Primary (config-read) path clamps retention to a non-negative floor
retention = max(0, config.get("retention_days", 30))

# WRONG — CLI override skips the clamp; a negative value slips through
retention = args.retention_days   # -1 bypasses the floor the config path enforces

# RIGHT — the override inherits the same clamp
retention = max(0, args.retention_days if args.retention_days is not None
                else config.get("retention_days", 30))
```

#### (d) Routing / dispatch-registration

A new subcommand alias must inherit the sibling dispatch contract. Determine the script's dispatch style first:

- If the script dispatches via a **string-keyed `COMMANDS`/dict map** (`handler = COMMANDS.get(args.command)`), the alias needs its OWN map key pointing at the same handler. `aliases=` on `add_parser` alone is necessary but **not** sufficient: argparse sets the `dest` to the exact alias the user typed, so an alias absent from the map falls through to the unknown-command branch.
- If the script dispatches via `set_defaults(func=...)` on each subparser, the subparser-level alias is sufficient (the bound `func` travels with whichever spelling matched).

Pin the alias with a **subprocess-level CLI test** — an in-process handler test invokes the handler directly and never exercises the routing layer, so it cannot catch the gap. See [`argument-naming.md`](../../../../plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md) Rule 2 for the accepted-secondary-spellings contract.

```python
COMMANDS = {"read": cmd_read, "get": cmd_read}   # alias gets its OWN key

# argparse side
p = subparsers.add_parser("read", aliases=["get"])

# WRONG — alias only on add_parser, missing from the map
COMMANDS = {"read": cmd_read}                     # `get` → COMMANDS.get("get") → None → unknown-command
subparsers.add_parser("read", aliases=["get"])

# RIGHT — alias present in BOTH the map and the subparser
COMMANDS = {"read": cmd_read, "get": cmd_read}
subparsers.add_parser("read", aliases=["get"])
```

#### (e) Normalization-before-decision

A new security/control-flow matcher over a trust-boundary input must canonicalize the input the same way sibling handlers do **before** comparing it against a deny/allow set. A raw-token or raw-substring match is bypassable by a near-miss spelling of the same input.

```python
# WRONG — raw-token program ban: bypassed by an absolute path
if program == "gh":            # "/usr/bin/gh" slips past
    reject()

# RIGHT — basename-strip before the program ban (sibling normalization)
if os.path.basename(program) == "gh":
    reject()

# WRONG — bare substring path-containment: "/safe-evil" matches "/safe"
if "/safe" in target_path:
    allow()

# RIGHT — segment/separator-anchored containment
if target_path == "/safe" or target_path.startswith("/safe/"):
    allow()
```

Apply the cheap self-review heuristic before shipping the matcher: *"what near-miss spelling of the input slips past this exact comparison?"*

#### (f) Input-parsing contract

A new producer-declared frontmatter opt-in field must inherit the sibling field-parsing contracts: read it from the `metadata:` block as a **direct child** (not a top-level key, and not a deeper `metadata.some_block.{key}`), and treat null/empty as **absent**. The membership test must require a non-empty string value after `.strip()` — not mere key-presence and not merely not-`None`. A bare `key:`, a `key: []`, or a quoted empty string is equivalent to absence.

```python
# Sibling opt-in field is read from metadata as a direct child, empty == absent
meta = frontmatter.get("metadata", {})
def opted_in(field):
    val = meta.get(field)
    return isinstance(val, str) and val.strip() != ""

# WRONG — new field read at top level, presence-only test
enabled = "new_flag" in frontmatter          # wrong nesting AND treats `new_flag:` as present

# RIGHT — new field inherits the sibling parsing contract
enabled = opted_in("new_flag")               # metadata-nested, non-empty-string required
```

### Author / reviewer checklist

Before shipping an element grafted beside established siblings, confirm each applicable facet:

- [ ] **(a) Guard clauses** — the new branch applies every precondition rejection its siblings apply before mutating shared state.
- [ ] **(b) Success-payload field contracts** — the new success return carries the full field set its sibling success branches return.
- [ ] **(c) Input-validation range clamps** — the parallel/override entry point applies the same range/format clamp as the primary path.
- [ ] **(d) Routing / dispatch-registration** — the alias is registered in the actual dispatch surface (map key AND/OR subparser), pinned by a subprocess-level CLI test.
- [ ] **(e) Normalization-before-decision** — the matcher canonicalizes the trust-boundary input the same way its siblings do before the deny/allow comparison.
- [ ] **(f) Input-parsing contract** — the new frontmatter field is read as a direct `metadata:` child with empty-as-absent semantics.
- [ ] A **cross-element contract test** (not just a happy-path test) asserts the new element and its sibling agree on the shared invariant.

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
| Directory names | MAY use hyphens | `run-config/`, `manage-run-config/` |
| Python files for import | MUST use underscores | `run_config.py`, `config_core.py` |
| Entry-point-only scripts | MAY use hyphens | `doctor-marketplace.py` (if never imported) |

### Recommended: Always Use Underscores

For consistency and future-proofing, prefer underscores for all Python files:

```text
scripts/
  run_config.py       # PASS Can be imported
  config_core.py      # PASS Can be imported
  cmd_timeout.py      # PASS Can be imported
```

### Anti-pattern

```text
scripts/
  run-config.py       # ✗ Cannot be imported
  manage-files.py     # ✗ Cannot be imported
```

## Direct Python Imports vs Subprocess

**Rule**: When script A needs functionality from script B, and both are Python, use direct imports instead of subprocess calls.

See `standards/cross-skill-integration.md` for complete details including PYTHONPATH setup, standard APIs, type ignore conventions, and when to use each approach.

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

## Script Quality Rules

Before marking script as "quality approved":

- Shebang: `#!/usr/bin/env python3`
- Stdlib-only (no pip dependencies)
- Subcommand pattern: `{noun}.py {verb}`
- Argparse with subparsers
- All arguments have help text
- Error handling with clear messages
- Exit codes (0 for success, 1 for error)
- Executable permissions set
- Test file exists and passes
- Scripts >400 lines are modularized by subcommand
- Uses `PLAN_DIR_NAME` env var for path construction (not hardcoded `.plan`)
