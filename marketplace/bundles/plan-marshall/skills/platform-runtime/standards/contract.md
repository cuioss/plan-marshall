# Platform Runtime TOON Contract

Per-operation TOON schemas for all 24 `platform-runtime` operations. Every operation returns one of three status variants: `success`, `error`, or `no-op`. Parser: `from toon_parser import parse_toon, serialize_toon` from `plan-marshall:ref-toon-format`.

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
| `unsupported_observable` | `wait for --observable` names a kind outside the closed enumerated set |
| `invalid_bound` | `wait for --bound-seconds` is not a positive number of seconds |
| `unknown_reference` | `wait for --reference` names no instance of the requested observable kind |
| `observable_unreachable` | The observable's inspection channel could not be reached; the wait was not held and **no outcome is implied** |
| `unexpected_observable_status` | The observable reported a status outside its documented vocabulary; the runtime refuses to infer an outcome from it |

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

Parse a store selector and an optional `--icon`, emit the OSC escape sequence directly to `/dev/tty` to repaint the current title in the terminal (Claude). No-op on OpenCode. This is the single repaint seam for blocking callers (lock/build acquire waits), for the `manage-status` phase-state-write drive seam, and for the `marshall-orchestrator` per-verb title repaint. When `--icon` is supplied it overrides the event-resolved icon for non-terminal phases; when omitted the composer applies its default active icon, so the push is a plain repaint of the current composed title. Router-dispatched in `platform_runtime.py`, abstract in `runtime_base.py`, concrete in `claude_runtime.py` (writes OSC sequence to `/dev/tty`) and `opencode_runtime.py` (returns no-op).

**Arguments**: `--store plans|orchestrator` (optional, default `plans`), `--plan-id <id>` (required with the default `plans` store), `--slug <slug>` (required with `--store orchestrator`), `--icon <icon>` (optional — omit for a plain repaint of the current title)

The two stores are mutually exclusive selectors for where the title state is read from: the default `plans` store resolves the plan's `status.json` by `--plan-id`, while `--store orchestrator` resolves the epic's `status.json` via `get_store_dir('orchestrator', slug)` by `--slug`. Supplying `--store orchestrator` without `--slug`, or the default store without `--plan-id`, returns `error: invalid_argument`.

`/dev/tty` is the **FALLBACK** delivery channel — the hook-written
`terminalSequence` envelope from `session render-title` is the primary one and
needs no tty ownership. A non-delivery is **reported**, not swallowed: `delivery`
names the channel on every `/dev/tty` attempt, and `reason` distinguishes the two
no-push outcomes.

**Success (Claude — push reached TTY, plans store)**:
```toon
status: success
operation: session push-title-token
plan_id: my-plan
pushed: true
delivery: dev_tty_fallback
```

**Success (Claude — push reached TTY, orchestrator store)**:
```toon
status: success
operation: session push-title-token
slug: my-epic
pushed: true
delivery: dev_tty_fallback
```

**Error (store selector missing its required identifier)**:
```toon
status: error
operation: session push-title-token
error: invalid_argument
message: --slug is required with --store orchestrator
```

**Success (Claude — no controlling terminal; the fallback channel could not land)**:
```toon
status: success
operation: session push-title-token
plan_id: my-plan
pushed: false
reason: no_controlling_tty
delivery: dev_tty_fallback
```

**Success (Claude — nothing to paint; the state read failed before any `/dev/tty` attempt)**:
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

### `session bind`

Bind the running session to `--plan-id` (last-driven-wins) so `session render-title` and `session resolve-plan` resolve the session to that plan. The caller's own `active-plan` cache slot is written unconditionally — no protect-active, no stale-slot reclaim, no plan-dir-exists check — so a session that switches to drive a different live plan rebinds cleanly. No-op on OpenCode (no platform-provided session id).

**Arguments**: `--plan-id <id>` (required), `--session-id <id>` (optional — falls back to `$CLAUDE_CODE_SESSION_ID`)

**Success (Claude — slot bound)**:
```toon
status: success
operation: session bind
plan_id: my-plan
session_id: abc123def456
bound: true
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: session bind
reason: OpenCode does not expose a platform-provided session id to the shell
alternative: Use OpenCode's built-in TUI status surface for plan visibility
```

---

### `session resolve-plan`

Read the running session's bound plan id — the read side of `session bind`. `session render-title` resolves the session→plan binding through the same read path. No-op on OpenCode (no platform-provided session id).

**Arguments**: `--session-id <id>` (optional — falls back to `$CLAUDE_CODE_SESSION_ID`)

**Success (Claude — bound)**:
```toon
status: success
operation: session resolve-plan
session_id: abc123def456
resolved: true
plan_id: my-plan
```

**Success (Claude — unbound slot)**:
```toon
status: success
operation: session resolve-plan
session_id: abc123def456
resolved: false
plan_id: ""
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: session resolve-plan
reason: OpenCode does not expose a platform-provided session id to the shell
alternative: Use OpenCode's built-in TUI status surface for plan visibility
```

---

### `session teardown`

Reset the terminal title to the terminal's own default and release the caller
session's plan binding — the end-of-session counterpart of `session bind` /
`session render-title`. Fired by the `SessionStart:clear` render trigger and by
`manage-status cmd_archive` after a plan directory is archived.

**Activation-gated, order load-bearing**: the activation signal is read FIRST. When
the terminal-title feature is not wired up (no render-hook entry on any
render-trigger event AND no `statusLine` command in either `.claude/settings.json`
or `.claude/settings.local.json`), the op writes NO title escape, opens NO
`/dev/tty`, mutates NO binding, and raises nothing. `reset` and `unbound` are
reported independently, so a landed title reset with a failed unbind (or the
reverse) is visible. Best-effort throughout: never raises, never changes the
caller's exit code. No-op on OpenCode.

**Arguments**: _(none)_

**Success (Claude — active, reset landed and slot dropped)**:
```toon
status: success
operation: session teardown
active: true
reset: true
unbound: true
```

**Success (Claude — active but no controlling terminal; the unbind still lands)**:
```toon
status: success
operation: session teardown
active: true
reset: false
unbound: true
```

**Success (Claude — feature not activated; nothing was touched)**:
```toon
status: success
operation: session teardown
active: false
reset: false
unbound: false
reason: feature_inactive
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: session teardown
reason: OpenCode has no terminal-title channel (issue anomalyco/opencode#8619)
alternative: Use OpenCode's built-in TUI status surface for plan visibility
```

---

### `session doctor`

Scan every per-session `active-plan` slot, build a plan→sessions reverse index, flag any plan bound by more than one live session (a conflict), and identify slots whose plan is archived/deleted (stale). With `--fix`, GC each stale slot. Keeps NO shared mutable index — the scan-then-GC is per-file and idempotent. No-op on OpenCode (no platform-provided session id).

**Arguments**: `--fix` (optional — GC stale slots whose plan is archived/deleted)

**Success (Claude — report)**:
```toon
status: success
operation: session doctor
fix: false
scanned: 12
conflict_count: 1
conflicts[1]:
- my-plan=sid-a,sid-b
stale_count: 1
stale[1]:
- sid-c=archived-plan
gc_removed: 0
```

**No-op (OpenCode)**:
```toon
status: no-op
operation: session doctor
reason: OpenCode does not expose a platform-provided session id to the shell
alternative: Use OpenCode's built-in TUI status surface for plan visibility
```

---

### `session reload-directive`

Resolve and surface the harness-appropriate post-upgrade reload directive after the executor / agent set is regenerated. RESOLVES + SURFACES only — a script cannot type a harness-level slash command, so the payload carries the directive TEXT for the operator/orchestrator to act on. Zero-touch is impossible in any harness.

**Arguments**: none

**Success (Claude — resolved directive)**:
```toon
status: success
operation: session reload-directive
directive: /reload-plugins
caveat: Only monitors require a full session restart; plan-marshall registers no monitors, so /reload-plugins picks up the regenerated executor / agent set live.
```

**No-op (OpenCode — restart alternative)**:
```toon
status: no-op
operation: session reload-directive
reason: OpenCode exposes no live plugin-reload command equivalent to Claude's /reload-plugins
alternative: Restart the OpenCode session to pick up the regenerated executor / agent set
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

### `wait for`

Hold a bounded wait until a **concrete, pollable observable** reaches a terminal state, and return a normalized, observable-independent outcome.

The `--observable` argument names a *kind* drawn from a closed enumerated set — it is deliberately **not** an opaque caller-supplied condition descriptor, because a runtime subprocess has no way to evaluate an arbitrary predicate and could only ever answer one with an unsubstantiated `unknown`. An unrecognised kind is rejected with `unsupported_observable` rather than silently awaited.

**Observable kinds**:

| Kind | `--reference` | Inspected surface |
|------|---------------|-------------------|
| `build-job` | The daemon-assigned `job_id` | The marshalld build-server job status surface, whose terminal vocabulary already distinguishes an externally killed job from a failed one |

**Arguments**: `--observable <kind>` (required), `--reference <id>` (required), `--bound-seconds <n>` (required, positive)

**Outcomes**: `succeeded`, `failed`, `timed_out`, `killed` (all `terminal: true`), and `pending` (`terminal: false`).

Two fail-closed rules are part of the contract. **Silence is not success**: the terminal-state set covers the failure signatures, so a negative outcome is reported as the negative outcome and never mistaken for continued waiting. **A bound is not a verdict**: exhausting `--bound-seconds` yields `outcome: pending` with `terminal: false` — an explicit unknown the caller must act on — never an implicit pass. An unreachable inspection channel is an `error`, likewise never a pass.

The governing policy — when to wait, who may hold a wait, and the tiered realisation — lives in `plan-marshall` `standards/waiting.md`; the placement decision is ADR-011.

**Success (terminal outcome)**:
```toon
status: success
operation: wait for
observable: build-job
reference: job-7f3a91
outcome: succeeded
terminal: true
elapsed_seconds: 47
bound_seconds: 600
```

**Success (bound exhausted — explicit unknown, NOT a pass)**:
```toon
status: success
operation: wait for
observable: build-job
reference: job-7f3a91
outcome: pending
terminal: false
elapsed_seconds: 600
bound_seconds: 600
```

**Success (terminal failure signature)**:
```toon
status: success
operation: wait for
observable: build-job
reference: job-7f3a91
outcome: killed
terminal: true
elapsed_seconds: 112
bound_seconds: 600
```

**Error (unrecognised observable kind)**:
```toon
status: error
operation: wait for
error: unsupported_observable
message: --observable 'ci-run' is not an inspectable observable kind; valid kinds: build-job
```

**Error (inspection channel unreachable)**:
```toon
status: error
operation: wait for
error: observable_unreachable
message: the build-job inspection channel could not be reached (socket_absent); the wait is not held and no outcome is implied
```

**No-op (OpenCode — no runtime-held wait channel)**:
```toon
status: no-op
operation: wait for
reason: OpenCode's runtime holds no wait channel — it has no platform-provided session id (issue #9292), no hook channel (issue anomalyco/opencode#8619), and no shared build layer to inspect an observable through, so a wait held here would be unobservable and could not be re-attached
alternative: Invoke the observable's own bounded-wait verb synchronously in-turn (build-server-client wait, ci checks wait), or checkpoint and re-dispatch to re-establish the wait from persisted state
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
