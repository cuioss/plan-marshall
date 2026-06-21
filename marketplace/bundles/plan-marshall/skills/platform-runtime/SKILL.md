---
name: platform-runtime
description: Platform abstraction layer routing operations to Claude Code or OpenCode implementations
user-invocable: false
mode: script-executor
---

# Platform Runtime Skill

Script-based platform abstraction that routes 18 goal-based operations to the correct target implementation. Follows the `tools-integration-ci` pattern: one router script, target-specific provider classes, static routing via `marshal.json`.

## Enforcement

**Execution mode**: Invoke scripts via executor notation; parse TOON output for `status` and route accordingly.

**Prohibited actions:**
- Do not call provider-specific scripts directly; all operations go through `platform_runtime.py`
- Do not invent script arguments not listed in the operations table
- Do not hard-code the target platform; routing is config-driven via `runtime.target` in `marshal.json`
- Do not implement ad-hoc TOON parsing; use the `ref-toon-format` parser module

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime <operation> [args...]`
- `session render-title` takes no arguments; all resolution is internal
- `no-op` responses are not errors; the calling skill must continue
- See `standards/contract.md` for per-operation TOON schemas

## What This Skill Provides

Eighteen operations covering the full platform lifecycle:

| Operation | Purpose |
|-----------|---------|
| `project initial-setup` | One-time project setup: create `.plan/`, seed `marshal.json`, install platform hook |
| `project install-hook` | Install the platform session hook into the target settings file |
| `layout skill-roots` | Resolve the ordered project-local skill root directories for the active target |
| `layout bundle-cache-root` | Resolve the deployed-bundle cache root directories for the active target |
| `session capture` | Persist current session id via `manage-status`; no-op on OpenCode |
| `permission configure` | Write raw permission list to platform settings |
| `permission analyze` | Read-only audit of permission hygiene, redundancy, and missing-steps |
| `permission fix` | Apply hygienic fixes: normalize, add, remove, ensure, consolidate |
| `permission ensure-wildcards` | Add marketplace bundle wildcard permissions |
| `permission ensure-steps` | Add missing skill permissions for `marshal.json` phase steps |
| `permission web-analyze` | Read-only analysis of WebFetch/webfetch domain permissions |
| `permission web-apply` | Add or remove web domain permissions |
| `session render-title` | Emit OSC title sequence from writer artifact; no-op on OpenCode |
| `session push-title-token` | Parse `--plan-id` and `--icon`, emit OSC escape to `/dev/tty` (Claude); no-op on OpenCode |
| `metrics capture` | Record token consumption for a planning phase |
| `metrics normalized-tokens` | Resolve normalized transcript token totals for the active target |
| `subagent dispatch` | Return platform-specific subagent invocation parameters |
| `health-check` | Verify platform integration |

See `standards/contract.md` for per-operation TOON schemas (success, error, no-op paths).

## Architecture

**Static Routing Pattern**: `marshal.json` stores `runtime.target`; router dispatches to target class.

```
marshal.json                                Scripts
runtime.target: claude  ──────────────────► claude_runtime.py
runtime.target: opencode ─────────────────► opencode_runtime.py
```

Router (`platform_runtime.py`) reads `runtime.target`, looks up target class in registry, and dispatches. Registry is extensible — adding a new target adds a class and a registry entry.

## Invocation

**Standard invocation (post-bootstrap):**
```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime <operation> [args...]
```

**Bootstrap invocation (Steps 1–3, before executor exists):**

During `marshall-steward` Steps 1–3 the executor does not yet exist. Use the glob-path bootstrap directly. After Step 4 (Generate Executor), switch to executor notation for all subsequent calls.

## TOON Contract

Every operation returns:

```toon
status: success | error | no-op
operation: <name>
result: <any>          (success only)
error: <string>        (error only)
message: <string>      (error only)
reason: <string>       (no-op only)
alternative: <string>  (no-op only)
```

Full per-operation schemas: `standards/contract.md`
No-op policy and caller obligations: `standards/no-op-policy.md`

## Error Codes

| Code | Meaning |
|------|---------|
| `invalid_scope` | Scope argument not `project` or `global` |
| `invalid_check` | `permission analyze --checks` contains unknown check name |
| `marshal_not_found` | `.plan/marshal.json` missing |
| `prompt_not_found` | `subagent dispatch` prompt file not found |
| `unknown_target` | `runtime.target` not in registry |
| `hook_not_configured` | SessionStart hook missing; `$CLAUDE_CODE_SESSION_ID` unset |

## No-Op Behavior

When a target returns `no-op`:
- `status` is `no-op`, not `error`
- `reason` explains why the operation is not supported
- `alternative` suggests what the caller can do instead
- **The calling skill must continue** — no-op is not a failure

## Compliance

All scripts comply with:
- **`tools-script-executor`** — executor notation, standardized error format, environment variables (`PLAN_DIR_NAME`, `PM_MARKETPLACE_ROOT`), exit codes (0 success, 1 invalid params, 2 runtime error)
- **`ref-toon-format`** — TOON generated and parsed via `toon_parser.py` from the `ref-toon-format` skill; no ad-hoc parsing

## Boundary

Platform-runtime operations satisfy: "Would this differ between Claude Code and OpenCode?"

| In scope | Belongs elsewhere |
|----------|-------------------|
| Platform hooks, session IDs | `manage-status` (plan state) |
| Settings/permissions files | `tools-integration-ci` (CI/PR) |
| Terminal title rendering | `manage-architecture` (architecture data) |
| Platform-specific subagent invocation | `manage-metrics` (metrics storage) |
| Platform health verification | `tools-script-executor` (executor regeneration) |

The `session render-title` and `session push-title-token` operations are the
resolve + emit layer of the terminal-title three-way split. They resolve
session → plan, read the title state from `status.json` (live first, archived
fallback), call the pure `manage-terminal-title` composer, and emit per platform
(OSC / statusLine / web sessionTitle, plus the `/dev/tty` push). `status.json` is
the single source of persisted title state — there is no `title-body.txt`
artifact. See `manage-terminal-title/standards/terminal-title-architecture.md` for
the canonical end-to-end architecture: state (`manage-status`), composer
(`manage-terminal-title`), resolve+emit (`platform-runtime`), session-plan
binding, output channels, platform abstraction, and the glyph + icon vocabulary.
