---
name: tools-script-executor
description: Universal script execution pattern via execute-script.py proxy
user-invocable: false
---

# Script Executor Skill

## Enforcement

**Execution mode**: All marketplace scripts must be executed through the executor proxy.

**Executor is cwd-pass-through. All cwd control is explicit at the call site.** See [standards/cwd-policy.md](standards/cwd-policy.md) for the single uniform cwd-relative resolution rule (ADR-002) and the cwd-unchanged invariant every script obeys.

**Prohibited actions:**
- Do not execute marketplace scripts directly by path; always use the executor notation
- Do not modify `.plan/execute-script.py` manually; regenerate via `/marshall-steward`
- Do not hard-code PYTHONPATH; the executor manages it automatically
- Do not rely on ambient cwd for path resolution inside scripts; follow [standards/cwd-policy.md](standards/cwd-policy.md)

**Constraints:**
- All scripts use `python3 .plan/execute-script.py {notation} {subcommand} {args}`
- Bootstrap pattern is only for first run when executor does not exist yet
- Plan-scoped logging requires `--plan-id` or `--audit-plan-id`
- Plan-metadata scripts resolve `.plan/` via `file_ops.get_base_dir()`, which uses the single uniform cwd walk-up (`set_base_dir()` → `PLAN_BASE_DIR` → nearest ancestor containing `.plan/local`; ADR-002) — main in phases 1-4, the pinned worktree in phase-5+. Worktree-scoped build / CI / Sonar scripts accept either `--plan-id` (auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir` (explicit override / escape hatch — the two flags are mutually exclusive); the merge lock is the single main-anchored resolver. See `standards/cwd-policy.md`

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
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request create --plan-id EXAMPLE-PLAN --title "My Task" --source description
# → parse `path` from the TOON output, then: Write(path, "Task details")
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read --plan-id EXAMPLE-PLAN

# File operations (generic files)
# Inline --content is reserved for single-line scalar values with no leading "#".
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write --plan-id EXAMPLE-PLAN --file notes-tag.txt --content "single line value with no newlines and no leading hash"

# For multi-line content (markdown, TOON, JSON) OR any payload whose first line begins with "#",
# stage the body to .plan/temp/{plan_id}/ via the Write tool first, then pass --content-file. See manage-files/SKILL.md § Enforcement for the binding rule.
# Write(.plan/temp/EXAMPLE-PLAN/notes.md) with the multi-line markdown body
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write --plan-id EXAMPLE-PLAN --file notes.md --content-file .plan/temp/EXAMPLE-PLAN/notes.md

# Build operations
python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "clean verify"

# References operations
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set --plan-id EXAMPLE-PLAN --field foo --value bar
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
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id EXAMPLE-PLAN --file task.md
```

**Example with --audit-plan-id** (audit logging only, stripped):
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --audit-plan-id EXAMPLE-PLAN --include-descriptions
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
  args: --plan-id EXAMPLE-PLAN --file missing.md
  stderr: FileNotFoundError: missing.md not found
```

See `plan-marshall:manage-logging` skill for full log format specification.

## Environment Variables

The executor exports environment variables to child scripts:

| Variable | Purpose | Default |
|----------|---------|---------|
| `PLAN_DIR_NAME` | Directory name for plan storage (e.g., `.plan`) | `.plan` |
| `PM_MARKETPLACE_ROOT` | Optional explicit marketplace anchor directory (must contain `marketplace/bundles`). NOT required for stale/relocated embedded paths — the executor self-heals those (see [Self-healing path resolution](#self-healing-path-resolution)). Honored by `generate_executor.py` and `script_shared.marketplace_paths.find_marketplace_path()` when resolving the marketplace tree. Overrides the script-relative walk and cwd-based fallback. The CLI flag `--marketplace-root` (on `generate` and `drift`) takes precedence when both are set. | _(unset)_ |
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

## Self-healing path resolution

The executor embeds an absolute-path `SCRIPTS` map at generation time. Those
paths can go stale when the checkout (or plugin cache) the executor was
generated against is relocated. `resolve_notation` self-heals automatically — a
stale embedded path is never returned blindly:

1. **Direct embedded hit** — returned only when the embedded path still exists
   on disk. A missing path is skipped, not returned.
2. **Prefix/substring shim** — same existence guard.
3. **Target-aware resolver** — discovers the script under the target's skill
   roots (Claude plugin cache `~/.claude/plugins/cache/plan-marshall/*/skills/…`,
   or the OpenCode config roots).
4. **cwd / executor-file upward walk** — walks up from both `Path.cwd()` and the
   executor file's own location looking for a live
   `marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py` (covers the
   dev-checkout case).

Because of this, `PM_MARKETPLACE_ROOT` is **not required** to recover from a
stale/relocated embedded path — it remains only as an intentional explicit
override for pinning discovery to a specific marketplace tree (see below).

## Setup

Run `/marshall-steward` to generate the executor after bundle changes.

### Pinning the marketplace anchor (worktrees / alternate checkouts)

A stale/relocated embedded path no longer needs an anchor — the executor
self-heals it (see [Self-healing path resolution](#self-healing-path-resolution)).
Pin discovery explicitly only when you deliberately want to force a *specific*
marketplace tree (e.g. invoking `generate_executor.py` from a worktree where
`Path.cwd()` would otherwise resolve to a different checkout). Two equivalent
mechanisms are supported; the CLI flag wins when both are set:

```bash
# Option A — CLI flag (preferred, single-call discipline)
python3 generate_executor.py generate --marketplace --marketplace-root /abs/path/to/checkout
python3 generate_executor.py drift    --marketplace --marketplace-root /abs/path/to/checkout

# Option B — env var as a SINGLE-COMMAND inline assignment. The assignment and
# the command MUST be one call; never a `cd`+`export` compound (an `export`
# does not persist across separate Bash calls, and the compound trips the Bash
# one-command-per-call / no-shell-constructs safety rules).
PM_MARKETPLACE_ROOT=/abs/path/to/checkout python3 /abs/path/to/checkout/.plan/execute-script.py <notation> ...
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

Resolve the bootstrap script path with the `Glob` tool against the pattern `~/.claude/plugins/cache/*/plan-marshall/*/skills/marshall-steward/scripts/bootstrap_plugin.py` and capture the first match as `{BOOTSTRAP_PLUGIN}`. Then invoke it directly:

```bash
python3 "{BOOTSTRAP_PLUGIN}" get-root
```

Output:
```
plugin_root	/Users/.../.claude/plugins/cache/plan-marshall
source	detected|cached
```

### Step 2: Execute Scripts Directly

Use the plugin root with a glob pattern for the version segment. Resolve the script path with the `Glob` tool against the pattern `${PLUGIN_ROOT}/plan-marshall/*/skills/<skill>/scr*ts/<script>.py` and capture the first match as `{SCRIPT_FILE}`. Then invoke it directly:

```bash
python3 "{SCRIPT_FILE}" <args>
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

## Broken Executor Recovery (Generated but Unrunnable)

This case is distinct from the [Bootstrap Pattern](#bootstrap-pattern-before-executor-exists) above. Bootstrap covers the **first-run** state where `.plan/execute-script.py` does **not yet exist**. This section covers the state where the generated executor **exists on disk but fails to run** — for example, a template import-surface change makes the embedded preamble import a symbol the runtime no longer exports, so every `python3 .plan/execute-script.py …` call aborts before reaching any script body. Because the executor itself is broken, the normal `/marshall-steward` and `/sync-plugin-cache` regeneration paths — which route through the executor — cannot be used to repair it.

### Recovery

Regenerate the executor by invoking `generate_executor.py` **directly**, bypassing the broken `.plan/execute-script.py`:

```bash
python3 marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py generate --marketplace --marketplace-root .
```

This is the same `generate_executor — generate` surface documented under [Canonical invocations](#canonical-invocations), run against the script file by its repository path rather than through the executor notation. The `--marketplace` flag selects the marketplace-source generation mode and `--marketplace-root .` pins discovery to the current checkout root (the directory that contains `marketplace/bundles`). After the direct call succeeds, the rewritten `.plan/execute-script.py` carries the corrected preamble and the normal executor-routed commands work again.

### Distinguishing the two executor-unavailable cases

| Case | Symptom | Recovery |
|------|---------|----------|
| First run (bootstrap) | `.plan/execute-script.py` does not exist | [Bootstrap Pattern](#bootstrap-pattern-before-executor-exists) — resolve the plugin root, run scripts directly |
| Broken generated executor | `.plan/execute-script.py` exists but every invocation fails before reaching a script body | Run `generate_executor.py generate --marketplace --marketplace-root .` directly to rebuild it |

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
# Outer shell timeout (600s) prevents the host platform from canceling
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks status --pr-number 123" \
  --success-field "status=success" \
  --failure-field "status=failure" \
  --command-key "ci:pr_checks"

# Explicit mode (custom interval)
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks status --pr-number 123" \
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
- `python3 {direct_script_path} ...`

## Canonical invocations

The canonical argparse surface for the two entry-point scripts this skill registers: `await_until.py` and `generate_executor.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### await_until

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd CHECK_CMD --success-field SUCCESS_FIELD --command-key COMMAND_KEY \
  [--failure-field FAILURE_FIELD] [--interval INTERVAL]
```

### generate_executor — generate

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate \
  [--force] [--dry-run] [--marketplace] [--marketplace-root PATH] [--target TARGET]
```

### generate_executor — verify

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor verify
```

### generate_executor — drift

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor drift \
  [--marketplace] [--marketplace-root PATH]
```

### generate_executor — paths

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor paths
```

### generate_executor — cleanup

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor cleanup \
  [--max-age-days MAX_AGE_DAYS]
```
