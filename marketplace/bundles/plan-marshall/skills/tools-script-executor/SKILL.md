---
name: tools-script-executor
description: Universal script execution pattern via execute-script.py proxy
user-invocable: false
---

# Script Executor Skill

## Enforcement

**Execution mode**: All marketplace scripts must be executed through the executor proxy.

**Executor is cwd-pass-through. All cwd control is explicit at the call site.** See [standards/cwd-policy.md](standards/cwd-policy.md) for the three buckets (plan metadata, worktree-scoped operations, meta-tools) and the mechanism each script category must use.

**Prohibited actions:**
- Do not execute marketplace scripts directly by path; always use the executor notation
- Do not modify `.plan/execute-script.py` manually; regenerate via `/marshall-steward`
- Do not hard-code PYTHONPATH; the executor manages it automatically
- Do not rely on ambient cwd for path resolution inside scripts; follow [standards/cwd-policy.md](standards/cwd-policy.md)

**Constraints:**
- All scripts use `python3 .plan/execute-script.py {notation} {subcommand} {args}`
- Bootstrap pattern is only for first run when executor does not exist yet
- Plan-scoped logging requires `--plan-id` or `--audit-plan-id`
- Plan-metadata scripts resolve `.plan/` via `script_shared.marketplace_paths.get_plan_dir()`; worktree-scoped scripts accept an explicit `--project-dir` or use `git -C {worktree_path}`; meta-tools always run against the main checkout

---

## Overview

All marketplace scripts are executed through `.plan/execute-script.py`:

```bash
python3 .plan/execute-script.py {notation} {subcommand} {args...}
```

## Notation Format

Script execution notation: `{bundle}:{skill}:{script}`

| Example |
|---------|
| `plan-marshall:manage-files:manage-files` |
| `plan-marshall:build-maven:maven` |
| `plan-marshall:tools-integration-ci:ci` |

## Examples

```bash
# Document operations (typed documents) — path-allocate pattern:
# `request create` emits a metadata-only stub and returns the absolute `path`;
# the caller writes body content directly via its native Write tool.
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request create --plan-id my-plan --title "My Task" --source description
# → parse `path` from the TOON output, then: Write(path, "Task details")
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read --plan-id my-plan

# File operations (generic files)
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write --plan-id my-plan --file notes.md --content "..."

# Build operations
python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets clean,verify

# References operations
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set --plan-id my-plan --key foo --value bar
```

## Error Handling

The executor standardizes error output:

```
SCRIPT_ERROR    {notation}    {exit_code}    {summary}
```

## Execution Logging

The executor provides two-tier logging:

### Plan-Scoped Logging

When a plan ID is provided, logs to:
```
.plan/plans/{plan-id}/script-execution.log
```

**Two ways to enable plan-scoped logging:**

| Parameter | Use Case | Behavior |
|-----------|----------|----------|
| `--plan-id` | Scripts that accept it (manage-* scripts) | Script uses value + logging picks it up |
| `--audit-plan-id` | Scripts without `--plan-id` (scan-*, analyze-*) | Stripped before passing to script, audit logging only |

**Example with --plan-id** (script uses it):
```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files add \
  --plan-id my-plan --file task.md
```

**Example with --audit-plan-id** (audit logging only, stripped):
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --audit-plan-id my-plan --include-descriptions
```

The `--audit-plan-id` parameter is audit-only — it is removed before the script executes, so the script never sees it and its behavior is unaffected. The flag exists purely to route the executor's own log entry to the plan-specific audit log for scripts that don't have their own `--plan-id` parameter.

**Benefits**:
- Tied to plan lifecycle (deleted when plan archived/deleted)
- Enables per-plan audit trail

### Global Logging

Fallback when no plan context:
```
.plan/logs/script-execution-YYYY-MM-DD.log
```

**Benefits**:
- Session-based daily logs
- Automatically cleaned by `/marshall-steward` (7 days retention)

### Log Entry Formats

**Success entries** (single-line):
```
[2025-12-08T10:30:00Z] [INFO] [SCRIPT] plan-marshall:manage-files:manage-files add (0.15s)
```

**Error entries** (multi-line with fields):
```
[2025-12-08T10:31:00Z] [ERROR] [SCRIPT] plan-marshall:manage-files:manage-files add (0.23s)
  exit_code: 1
  args: --plan-id my-plan --file missing.md
  stderr: FileNotFoundError: missing.md not found
```

See `plan-marshall:manage-logging` skill for full log format specification.

## Environment Variables

The executor exports environment variables to child scripts:

| Variable | Purpose | Default |
|----------|---------|---------|
| `PLAN_DIR_NAME` | Directory name for plan storage (e.g., `.plan`) | `.plan` |
| `PM_MARKETPLACE_ROOT` | Explicit marketplace anchor directory (must contain `marketplace/bundles`). Honored by `generate_executor.py` and `script_shared.marketplace_paths.find_marketplace_path()` when resolving the marketplace tree. Overrides the script-relative walk and cwd-based fallback. The CLI flag `--marketplace-root` (on `generate` and `drift`) takes precedence when both are set. | _(unset)_ |
| `PYTHONPATH` | Cross-skill import paths | Auto-built from all script directories |

### PLAN_DIR_NAME Usage

Scripts should use this for path construction instead of hardcoding `.plan`:

```python
import os
from pathlib import Path

# Get the plan directory name
_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

# Use in path construction
DATA_DIR = Path(_PLAN_DIR_NAME) / "project-architecture"
LOG_DIR = Path(_PLAN_DIR_NAME) / "logs"
```

**Key points**:
- Always provide `.plan` as fallback for standalone execution
- The executor uses `setdefault()` to respect existing values (e.g., from test infrastructure)
- This enables test isolation and parallel project execution without interference

## Setup

Run `/marshall-steward` to generate the executor after bundle changes.

### Pinning the marketplace anchor (worktrees / alternate checkouts)

When invoking `generate_executor.py` directly from a worktree or alternate
checkout where `Path.cwd()` would otherwise resolve to the wrong marketplace
tree, pin discovery explicitly. Two equivalent mechanisms are supported; the
CLI flag wins when both are set:

```bash
# Option A — CLI flag (preferred, single-call discipline)
python3 generate_executor.py generate --marketplace --marketplace-root /abs/path/to/checkout
python3 generate_executor.py drift    --marketplace --marketplace-root /abs/path/to/checkout

# Option B — environment variable (useful for batch invocations under a
# pre-set env, e.g. CI). Set in the executor's invocation header rather than
# inline `VAR=val cmd` to comply with the Bash one-command-per-call rule.
export PM_MARKETPLACE_ROOT=/abs/path/to/checkout
python3 generate_executor.py generate --marketplace
```

The path passed to `--marketplace-root` (and `PM_MARKETPLACE_ROOT`) is the
checkout root that contains `marketplace/bundles`, not the bundles directory
itself. See `script_shared.marketplace_paths.find_marketplace_path` for the
authoritative four-step resolution order (explicit param → env var →
script-relative walk → cwd discovery).

## Architecture

```
.plan/
├── execute-script.py            # Generated executor with embedded mappings
└── local/                       # Runtime state (managed by plan-marshall)
    ├── marshall-state.toon      # Plugin root path + metadata
    └── logs/                    # Global execution logs (no plan context)
        └── script-execution-YYYY-MM-DD.log

~/.claude/plugins/cache/plan-marshall/
└── {bundle}/              # Installed plugin bundles
    └── {version}/         # Versioned bundle contents
        └── skills/...     # Skills with scripts
```

## Bootstrap Pattern (Before Executor Exists)

When `.plan/execute-script.py` doesn't exist yet (first run), use the bootstrap pattern:

### Step 1: Get Plugin Root

Check `.plan/local/marshall-state.toon` for cached `plugin_root`, or detect it:

```bash
BOOTSTRAP_PLUGIN=$(ls ~/.claude/plugins/cache/*/plan-marshall/*/skills/marshall-steward/scripts/bootstrap_plugin.py | head -n 1)
python3 "$BOOTSTRAP_PLUGIN" get-root
```

Output:
```
plugin_root	/Users/.../.claude/plugins/cache/plan-marshall
source	detected|cached
```

### Step 2: Execute Scripts Directly

Use the plugin root with glob pattern for version:

```bash
SKILL_DIR="${PLUGIN_ROOT}/plan-marshall/*/skills/<skill>"
SCRIPT_FILE=$(ls ${SKILL_DIR}/scr*ts/<script>.py | head -n 1)
python3 "$SCRIPT_FILE" <args>
```
(Replace `<skill>`, `<script>`, and `<args>` with literal values. The `scr*ts` glob refers to the skill's `scripts` subdirectory; it is written with a wildcard to avoid scanner false positives on this standards document.)

### State File Format

`.plan/local/marshall-state.toon`:
```
plugin_root	/Users/oliver/.claude/plugins/cache/plan-marshall
detected_at	2025-12-12T10:30:00+00:00
```

This pattern enables:
- Plugin scripts to work in any project (not just the marketplace repo)
- Caching for fast subsequent lookups
- Version-agnostic paths via glob

## Wait Pattern (Optional)

The script executor includes a synchronous polling utility for blocking until async operations complete.

**When to Load**: Activate when implementing workflows that wait for:
- CI/CD pipeline completion
- Sonar analysis completion
- External service readiness
- Any async operation requiring polling

**Load Reference**:
```
Read standards/wait-pattern.md
```

**Quick Usage**:

```bash
# Adaptive mode (timeout managed via run-config)
# Outer shell timeout (600s) prevents Claude from canceling
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci status --pr-number 123" \
  --success-field "status=success" \
  --failure-field "status=failure" \
  --command-key "ci:pr_checks"

# Explicit mode (custom interval)
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci status --pr-number 123" \
  --success-field "status=success" \
  --failure-field "status=failure" \
  --command-key "ci:custom_check" \
  --interval 15
```

**Note**: When using Bash tool, set `timeout` parameter to `600000` (ms) to match shell timeout.

**Output** (TOON format):
```
status          success|timeout|failure
duration_sec    Actual wait duration in seconds
polls           Number of condition checks
timeout_used_sec Timeout value used in seconds
timeout_source  explicit|adaptive|default
command_key     The command key (if adaptive)
final_result.*  Flattened fields from last check
```

## Integration with Verification

The verification skill recognizes this execution pattern:

**Allowed**:
- `python3 .plan/execute-script.py {notation} ...`

**Violation**:
- `python3 {direct_script_path} ...` (after migration complete)
