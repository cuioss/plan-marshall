---
name: platform-runtime
description: Platform abstraction layer routing operations to Claude Code or OpenCode implementations
user-invocable: false
mode: script-executor
---

# Platform Runtime Skill

Script-based platform abstraction that routes 24 goal-based operations to the correct target implementation. Follows the `tools-integration-ci` pattern: one router script, target-specific provider classes, static routing via `marshal.json`.

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

Twenty-four operations covering the full platform lifecycle:

| Operation | Purpose |
|-----------|---------|
| `project initial-setup` | One-time project setup: create `.plan/`, seed `marshal.json`, install platform hook |
| `project install-hook` | Install the terminal-title hook bundle; with the orthogonal `--enforcement` opt-in, install ONLY the PreToolUse enforcement hook entry without touching the terminal-title wiring |
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
| `session push-title-token` | Parse the store selector (`--plan-id` for the plan store, or `--store orchestrator --slug {slug}` for the orchestrator store) plus optional `--icon`, emit OSC escape to `/dev/tty` (Claude); no-op on OpenCode. This is the single repaint seam for blocking callers, the `manage-status` phase-state-write drive seam, and the `marshall-orchestrator` per-verb title repaint; `--icon` omitted composes a plain repaint of the current title. `/dev/tty` is the FALLBACK channel (the hook-written `terminalSequence` is primary), and a non-delivery is reported as `pushed: false` with `reason: no_controlling_tty` and `delivery: dev_tty_fallback` |
| `session bind` | Bind the running session to `--plan-id` (last-driven-wins) so `render-title` / `resolve-plan` resolve it; no-op on OpenCode |
| `session resolve-plan` | Read the running session's bound plan id (the read side of `session bind`); no-op on OpenCode |
| `session doctor` | Scan every per-session active-plan slot, report plan-bound-by-multiple-sessions conflicts, and (with `--fix`) GC stale slots; no-op on OpenCode |
| `session teardown` | Activation-gated end-of-session retire: reset the tab to the terminal's own default (bare OSC-0) and drop the session's plan binding; a project with no terminal-title wiring reports `active: false` / `reason: feature_inactive` and is left untouched. No arguments; no-op on OpenCode |
| `session reload-directive` | Resolve + surface the harness-appropriate post-upgrade reload directive (Claude: `/reload-plugins` plus the monitor caveat); no-op (full-restart alternative) on OpenCode. RESOLVES + SURFACES only — a script cannot type a harness slash command |
| `metrics capture` | Record token consumption for a planning phase |
| `metrics normalized-tokens` | Resolve normalized transcript token totals for the active target |
| `subagent dispatch` | Return platform-specific subagent invocation parameters |
| `wait for` | Hold a bounded wait until a concrete, pollable observable (`--observable` names a kind from a closed set; `build-job` today) reaches a terminal state, and return a normalized `succeeded`/`failed`/`timed_out`/`killed`/`pending` outcome. The observable is never an opaque condition descriptor — a runtime subprocess cannot evaluate one. Bound exhaustion yields `outcome: pending` with `terminal: false`, never an implicit pass; no-op on OpenCode, whose runtime holds no wait channel |
| `health-check` | Verify platform integration |

See `standards/contract.md` for per-operation TOON schemas (success, error, no-op paths).

The `health-check --checks display` surface inspects each terminal-title render entry plus a dedicated `PreToolUse:enforcement` present/MISSING label for the orthogonal enforcement hook, so a partial or absent enforcement install is diagnosable and repairable independently of the terminal-title wiring.

## Architecture

**Static Routing Pattern**: `marshal.json` stores `runtime.target`; router dispatches to target class.

```text
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
| `invalid_settings` | Settings file malformed (JSON parse error); fail-closed before write — `permission configure/fix/ensure-wildcards/ensure-steps/web-apply` |
| `invalid_marshal` | `.plan/marshal.json` malformed (parse error); fail-closed instead of zero-step audit — `permission analyze/ensure-steps` |
| `unsupported_observable` | `wait for --observable` names a kind outside the closed set |
| `invalid_bound` | `wait for --bound-seconds` is not positive |
| `unknown_reference` | `wait for --reference` names no instance of the observable kind |
| `observable_unreachable` | The observable's inspection channel could not be reached; no outcome is implied |
| `unexpected_observable_status` | The observable reported an out-of-vocabulary status; no outcome is inferred |

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
| Post-upgrade reload directive (harness-appropriate) | `marshall-steward` (upgrade flow that consumes the directive) |

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

## PreToolUse Enforcement Hook

A conditional PreToolUse enforcement hook deterministically blocks four
mechanically-checkable hard-rule violation families, but ONLY when the call
originates inside a plan-marshall plan context — failing open everywhere else.
It is implemented by three sibling scripts:

- `pretooluse_gate.py` — the shared, pure-function module that is the SINGLE
  home of the PreToolUse payload-field knowledge and the `Signal1 OR Signal2`
  fail-open context-gate predicate. Imported by both leaves below; owns no rule
  matchers.
- `claude_pretooluse_capture.py` — the observe-only leaf that validates the
  shared gate's field names against real payloads before enforcement is armed.
- `claude_pretooluse_hook.py` — the enforcement leaf that imports the shared
  gate and adds only the four rule families plus the `permissionDecision: deny`
  envelope.

The enforcement hook is installed on demand via the orthogonal
`project install-hook --enforcement` path (independent of the terminal-title
bundle), surfaces a dedicated `PreToolUse:enforcement` present/MISSING label on
the `health-check --checks display` diagnostic, and is registered through the
marshall-steward Configuration → Enforcement Hook menu
([`../marshall-steward/references/menu-enforcement-hook.md`](../marshall-steward/references/menu-enforcement-hook.md)).
The context gate, the four rule families with their redirect reasons, the
fail-open / best-effort-no-raise contract, and the capture-validates-the-gate
dependency chain are documented in
[`standards/pretooluse-enforcement.md`](standards/pretooluse-enforcement.md) —
the canonical reference; the rule list is not restated here.
