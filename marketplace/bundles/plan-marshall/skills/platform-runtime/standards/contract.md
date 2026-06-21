# Platform Runtime TOON Contract

Per-operation TOON schemas for all 18 `platform-runtime` operations. Every operation returns one of three status variants: `success`, `error`, or `no-op`. Parser: `from toon_parser import parse_toon, serialize_toon` from `plan-marshall:ref-toon-format`.

**Invocation pattern**:
```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime <operation> [args...]
```

---

## Common Shapes

### Base success envelope
```toon
status: success
operation: <operation-name>
```

### Base error envelope
```toon
status: error
operation: <operation-name>
error: <error-code>
message: <human-readable explanation>
```

### Base no-op envelope
```toon
status: no-op
operation: <operation-name>
reason: <why the operation is not supported on this target>
alternative: <what the caller can do instead>
```

`no-op` is not an error. The calling skill must continue after receiving `no-op`.

---

## Error Codes

| Code | Meaning |
|------|---------|
| `invalid_scope` | `--scope` not `project` or `global` |
| `invalid_check` | `permission analyze --checks` contains an unknown check name |
| `marshal_not_found` | `.plan/marshal.json` missing |
| `prompt_not_found` | `subagent dispatch --prompt-file` path not found |
| `unknown_target` | `runtime.target` value not in the target registry |
| `hook_not_configured` | SessionStart hook not installed; `$CLAUDE_CODE_SESSION_ID` unset |
| `invalid_settings` | Settings file is malformed (JSON parse error); fail-closed before any write so a malformed file is never clobbered — returned by `permission configure`, `permission fix`, `permission ensure-wildcards`, `permission ensure-steps`, `permission web-apply` |
| `invalid_marshal` | `.plan/marshal.json` is malformed (parse error); fail-closed instead of degrading to a zero-step audit — returned by `permission analyze`, `permission ensure-steps` |

---

## Operations

### `project initial-setup`

One-time project setup: create `.plan/`, seed `marshal.json`, install platform hook.

**Arguments**: `--project-dir <path>` (default `.`), `--target claude|opencode` (default `claude`)

**Success**:
```toon
status: success
operation: project initial-setup
target: claude
project_dir: /path/to/project
marshal_written: true
hook_installed: true
```

**Success (OpenCode — no hook)**:
```toon
status: success
operation: project initial-setup
target: opencode
project_dir: /path/to/project
marshal_written: true
hook_installed: false
hook_skip_reason: OpenCode does not support a SessionStart hook equivalent (issue #9292)
```

**Error**:
```toon
status: error
operation: project initial-setup
error: unknown_target
message: Target 'foobar' is not in the registry; valid targets are: claude, opencode
```

---

### `project install-hook`

Install only the SessionStart hook into a caller-specified settings file. Unlike `project initial-setup`, this does not create `.plan/` or seed `marshal.json` — it is the targeted hook-installation primitive. Idempotent: re-invocation when the hook is already present makes no change.

**Arguments**: `--target <settings-file-path>` (required)

**Success (Claude — hook installed)**:
```toon
status: success
operation: project install-hook
target: .claude/settings.local.json
hook_installed: true
already_present: false
```

**Success (Claude — hook already present)**:
```toon
status: success
operation: project install-hook
target: .claude/settings.local.json
hook_installed: true
already_present: true
```

**Error (Claude — write failure)**:
```toon
status: error
operation: project install-hook
error: io_error
message: Failed to install SessionStart hook into .claude/settings.local.json
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: project install-hook
reason: OpenCode has no Claude-style SessionStart settings hook to install (issue anomalyco/opencode#8619)
alternative: Use OpenCode's built-in session mechanism for plan visibility
```

---

### `layout skill-roots`

Resolve the ordered project-local skill root directories for the active target.

**Arguments**: _(none)_

**Success**:
```toon
status: success
operation: layout skill-roots
target: claude
roots[1]:
- .claude/skills
```

---

### `layout bundle-cache-root`

Resolve the deployed-bundle cache root directories for the active target.

**Arguments**: _(none)_

**Success**:
```toon
status: success
operation: layout bundle-cache-root
target: claude
roots[1]:
- /Users/me/.claude/plugins/cache/plan-marshall
```

---

### `session capture`

Persist the current platform session identifier via `manage-status`.

**Arguments**: `--plan-id <id>` (required)

**Success (Claude)**:
```toon
status: success
operation: session capture
plan_id: my-plan
session_id: abc123def456
stored: true
```

**Error (Claude — hook not configured)**:
```toon
status: error
operation: session capture
error: hook_not_configured
message: $CLAUDE_CODE_SESSION_ID is unset; run marshall-steward to install the SessionStart hook
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: session capture
reason: OpenCode does not expose a platform-provided session id to the shell; tracked upstream at issue #9292
alternative: pass --total-tokens manually to metrics capture
```

---

### `permission configure`

Write a raw permission list to the target platform's settings.

**Arguments**: `--scope project|global` (required), `--permissions <pattern> [<pattern>...]` (required)

**Success**:
```toon
status: success
operation: permission configure
scope: project
permissions_written: 3
target_file: .claude/settings.local.json
```

**Error**:
```toon
status: error
operation: permission configure
error: invalid_scope
message: --scope must be 'project' or 'global'; got 'local'
```

**Error (malformed settings — fail-closed)**:
```toon
status: error
operation: permission configure
error: invalid_settings
message: settings file is malformed JSON; refusing to overwrite
```

---

### `permission analyze`

Read-only audit of permission configuration for hygiene, security, and completeness.

**Arguments**: `--scope global|project|both` (required), `--checks redundant,suspicious,missing-steps,all` (required), `--marshal <path>` (required when `missing-steps` check included)

**Success**:
```toon
status: success
operation: permission analyze
scope: both
checks_run[3]:
- redundant
- suspicious
- missing-steps
total_findings: 3

findings[3]{check,severity,details}:
redundant	info	Bash(git:*) present in both global and project settings
suspicious	medium	Write(/tmp/**) is a broad write permission; consider scoping to a specific path
missing-steps	high	project:finalize-step-plugin-doctor in phase-6-finalize has no matching skill permission

summary:
  high: 1
  medium: 1
  info: 1
```

**Success (no findings)**:
```toon
status: success
operation: permission analyze
scope: project
checks_run[2]:
- redundant
- suspicious
total_findings: 0
```

**Error**:
```toon
status: error
operation: permission analyze
error: invalid_check
message: Unknown check 'typo'; valid checks are: redundant, suspicious, missing-steps, all
```

**Error (malformed marshal — fail-closed)**:
```toon
status: error
operation: permission analyze
error: invalid_marshal
message: .plan/marshal.json is malformed JSON; cannot audit missing-steps
```

---

### `permission fix`

Apply hygienic fixes to permission configuration.

**Arguments**: `--scope project|global` (required), `--operation normalize|add|remove|ensure|consolidate` (required), `--permissions <pattern> [...]` (for `add`, `remove`, `ensure`), `--dry-run` (optional)

**Success**:
```toon
status: success
operation: permission fix
scope: project
fix_operation: normalize
dry_run: false
target_file: .claude/settings.local.json
changes_applied: 4
```

**Success (dry-run)**:
```toon
status: success
operation: permission fix
scope: project
fix_operation: add
dry_run: true
target_file: .claude/settings.local.json
changes_applied: 0

proposed_additions[1]:
- Bash(python3 scripts/*.py)
```

**Error**:
```toon
status: error
operation: permission fix
error: invalid_scope
message: --scope must be 'project' or 'global'; got 'both'
```

**Error (malformed settings — fail-closed)**:
```toon
status: error
operation: permission fix
error: invalid_settings
message: settings file is malformed JSON; refusing to overwrite
```

---

### `permission ensure-wildcards`

Ensure all marketplace bundle wildcards exist so skills and commands are accessible without prompting.

**Arguments**: `--scope project|global` (required), `--marketplace-dir <path>` (default `marketplace/`), `--dry-run` (optional)

**Success**:
```toon
status: success
operation: permission ensure-wildcards
scope: project
marketplace_dir: marketplace/
dry_run: false
bundles_scanned: 10
wildcards_added: 3
wildcards_already_present: 7
target_file: .claude/settings.local.json
```

**Error**:
```toon
status: error
operation: permission ensure-wildcards
error: invalid_scope
message: --scope must be 'project' or 'global'; got 'all'
```

**Error (malformed settings — fail-closed)**:
```toon
status: error
operation: permission ensure-wildcards
error: invalid_settings
message: settings file is malformed JSON; refusing to overwrite
```

---

### `permission ensure-steps`

For each `project:{skill}` step in `marshal.json` phases 5 and 6, ensure a matching skill permission exists.

**Arguments**: `--marshal <path>` (required), `--scope project|global` (required), `--dry-run` (optional)

**Success**:
```toon
status: success
operation: permission ensure-steps
marshal: .plan/marshal.json
scope: project
dry_run: false
steps_scanned: 8
permissions_added: 2
permissions_already_present: 6
target_file: .claude/settings.local.json
```

**Success (dry-run)**:
```toon
status: success
operation: permission ensure-steps
marshal: .plan/marshal.json
scope: project
dry_run: true
steps_scanned: 8
permissions_added: 0

proposed_additions[2]:
- Skill(finalize-step-plugin-doctor)
- Skill(finalize-step-sync-plugin-cache)
```

**Error**:
```toon
status: error
operation: permission ensure-steps
error: marshal_not_found
message: .plan/marshal.json not found; run 'project initial-setup' first
```

**Error (malformed marshal — fail-closed)**:
```toon
status: error
operation: permission ensure-steps
error: invalid_marshal
message: .plan/marshal.json is malformed JSON; cannot scan steps
```

---

### `permission web-analyze`

Read-only analysis of WebFetch / webfetch domain permissions.

**Arguments**: `--scope global|project|both` (required)

**Success**:
```toon
status: success
operation: permission web-analyze
scope: both
total_domains: 6

domains[6]{domain,category,scope,duplicate}:
github.com	major	global	false
api.github.com	major	global	false
example.com	unknown	project	false
github.com	major	project	true
raw.githubusercontent.com	major	global	false
suspicious-domain.xyz	suspicious	project	false
```

**Error**:
```toon
status: error
operation: permission web-analyze
error: invalid_scope
message: --scope must be 'global', 'project', or 'both'; got 'all'
```

---

### `permission web-apply`

Add or remove web domain permissions.

**Arguments**: `--scope project|global` (required), `--add <json-array>` (optional), `--remove <json-array>` (optional), `--dry-run` (optional)

**Success**:
```toon
status: success
operation: permission web-apply
scope: project
dry_run: false
domains_added: 2
domains_removed: 1
target_file: .claude/settings.local.json
```

**Error**:
```toon
status: error
operation: permission web-apply
error: invalid_scope
message: --scope must be 'project' or 'global'; got 'both'
```

**Error (malformed settings — fail-closed)**:
```toon
status: error
operation: permission web-apply
error: invalid_settings
message: settings file is malformed JSON; refusing to overwrite
```

---

### `session render-title`

Resolve session → plan, read the title state from `status.json` (live first,
archived fallback), compose via the pure `manage-terminal-title` composer, and
emit the result. Hook mode emits a JSON envelope (`terminalSequence` for every
event, plus a gated web/desktop `sessionTitle`); statusLine mode (`--statusline`)
emits plain `{icon} {glyph} {body}` text. All session → plan resolution is
internal; the only argument is the optional mode flag.

**Arguments**: `--statusline` _(optional — selects statusLine output mode instead of the hook JSON envelope)_

**Success (Claude)**:
```toon
status: success
operation: session render-title
plan_id: my-plan
title_body: pm:execute:implement-feature
emitted: true
```

**No-op (Claude — session not captured)**:
```toon
status: no-op
operation: session render-title
reason: $CLAUDE_CODE_SESSION_ID is unset; session capture has not run
alternative: run marshall-steward to install the SessionStart hook, then re-enter the plan phase
```

**No-op (Claude — no active plan)**:
```toon
status: no-op
operation: session render-title
reason: no active plan registered for this session
alternative: start a plan phase so manage-status can register the session
```

**No-op (Claude — no title state)**:
```toon
status: no-op
operation: session render-title
reason: no plan-title to render; status.json has an empty or missing current_phase
alternative: the title will resume on the next mutation that writes current_phase to status.json
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: session render-title
reason: OpenCode has no plugin-driven terminal-title hook (issue anomalyco/opencode#8619)
alternative: Use OpenCode's built-in TUI status surface for plan visibility
```

---

### `session push-title-token`

Parse `--plan-id` and `--icon`, emit the OSC escape sequence directly to `/dev/tty` to push the current title-token state into the terminal title (Claude). No-op on OpenCode. Router-dispatched in `platform_runtime.py`, abstract in `runtime_base.py`, concrete in `claude_runtime.py` (writes OSC sequence to `/dev/tty`) and `opencode_runtime.py` (returns no-op).

**Arguments**: `--plan-id <id>` (required), `--icon <icon>` (required)

**Success (Claude — push reached TTY)**:
```toon
status: success
operation: session push-title-token
plan_id: my-plan
pushed: true
```

**Success (Claude — silent no-op, TTY not openable or no title state)**:
```toon
status: success
operation: session push-title-token
plan_id: my-plan
pushed: false
reason: no_title_state
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: session push-title-token
reason: OpenCode has no plugin-driven terminal-title hook; OSC escape push not supported
alternative: Use OpenCode's built-in TUI status surface for plan visibility
```

---

### `metrics capture`

Record token consumption for a planning phase.

**Arguments**: `--plan-id <id>` (required), `--phase <phase>` (required), `--total-tokens <n>` (optional)

**Success (Claude)**:
```toon
status: success
operation: metrics capture
plan_id: my-plan
phase: execute
session_id: abc123def456
tokens_captured: 12450
cursor_updated: true
```

**No-op (Claude — session id missing)**:
```toon
status: no-op
operation: metrics capture
reason: Session ID found but transcript/DB query returned no usage data for this phase
alternative: Pass --total-tokens manually
```

**Success (OpenCode — manual tokens)**:
```toon
status: success
operation: metrics capture
plan_id: my-plan
phase: execute
tokens_captured: 8000
source: manual
```

**No-op (OpenCode — no manual tokens)**:
```toon
status: no-op
operation: metrics capture
reason: automatic token capture requires a platform-provided session id, which OpenCode does not expose (issue #9292)
alternative: pass --total-tokens manually
```

---

### `metrics normalized-tokens`

Resolve normalized transcript token totals for the active target. Walks the session transcript, writes the per-phase `{input, output, cache_read, cache_creation, total, billing_weighted_total, subagent_*}` view to `--output-file` as JSON, and returns the attribution counters. `total` is the canonical four-field sum (`input + output + cache_read + cache_creation`); `billing_weighted_total` is reported separately.

**Arguments**: `--session-id <id>` (required), `--window <phase> <start> <end>` (repeatable), `--output-file <path>` (required)

**Success**:
```toon
status: success
operation: metrics normalized-tokens
session_id: 21df86b6-731d-4b88-8ad0-507e05a872fa
output_file: .plan/plans/my-plan/work/normalized-tokens.json
phases_attributed: 6
message_count: 412
subagent_phases_attributed: 4
subagent_calls_attributed: 11
subagent_transcripts_walked: 11
four_field_phases_attributed: 6
```

**No-op (no transcript located)**:
```toon
status: no-op
operation: metrics normalized-tokens
reason: transcript_not_found
alternative: pass --total-tokens manually to metrics capture
```

**Error (output write failed)**:
```toon
status: error
operation: metrics normalized-tokens
error: io_error
message: Failed to write normalized-token result to <path>: <reason>
```

---

### `subagent dispatch`

Return the platform-specific invocation parameters for spawning a focused subagent.

**Arguments**: `--agent <name>` (required), `--prompt-file <path>` (optional), `--context <json>` (optional)

**Success (Claude)**:
```toon
status: success
operation: subagent dispatch
platform: claude

invocation:
  tool: Task
  description: Run phase-3-outline outline
  prompt: ...agent body with context merged...
  subagent_type: execution-context-level-3
```

**Success (OpenCode)**:
```toon
status: success
operation: subagent dispatch
platform: opencode

invocation:
  tool: task
  description: Run phase-3-outline outline
  prompt: ...agent body with context merged...
  subagent_type: execution-context-level-3
```

**No-op (unmapped tools)**:
```toon
status: no-op
operation: subagent dispatch
reason: Agent team-coordinator-agent requires unmapped tools: SendMessage
alternative: Remove unsupported tools from agent frontmatter or inline the agent logic
```

**Error (prompt file not found)**:
```toon
status: error
operation: subagent dispatch
error: prompt_not_found
message: prompt file not found: prompts/my-prompt.md
```

---

### `health-check`

Verify platform integration.

**Arguments**: `--checks all|permissions|display|mcp-diagnostics` (required)

**Success (all checks passing)**:
```toon
status: success
operation: health-check
checks_run[4]:
- permissions
- display
- mcp-diagnostics
- hook

all_healthy: true

results[4]{check,healthy,detail}:
permissions	true	settings.local.json present; allow array has 12 entries
display	true	render-title hook entry present in .claude/settings.local.json
mcp-diagnostics	true	MCP server reachable at 127.0.0.1:64342
hook	true	SessionStart hook entry present in .claude/settings.json
```

**Success (some checks failing)**:
```toon
status: success
operation: health-check
checks_run[2]:
- permissions
- hook

all_healthy: false

results[2]{check,healthy,detail}:
permissions	true	settings.local.json present; allow array has 12 entries
hook	false	SessionStart hook entry missing from .claude/settings.json; run marshall-steward to install
```

**Error**:
```toon
status: error
operation: health-check
error: marshal_not_found
message: .plan/marshal.json not found; run 'project initial-setup' first
```
