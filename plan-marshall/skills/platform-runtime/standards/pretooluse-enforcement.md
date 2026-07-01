# PreToolUse Enforcement Hook

The conditional PreToolUse enforcement hook deterministically blocks four
mechanically-checkable hard-rule violation families — but ONLY when the call
originates inside a plan-marshall plan context. Every other call passes through
untouched. This document is the canonical reference for the hook's context gate,
rule families, fail-open contract, the capture-validates-the-gate dependency
chain, and the on-demand registration model.

## Components

Three scripts in `scripts/` implement the hook, layered shared-gate-first:

| Script | Role |
|--------|------|
| `pretooluse_gate.py` | Shared, pure-function library: the SINGLE home of payload-field knowledge and the context-gate predicate. Imported by both leaves; owns NO rule matchers. |
| `claude_pretooluse_capture.py` | Observe-only leaf that imports the shared gate and records the raw payload + the gate's extracted fields + would-be verdict. Always exits 0 emitting nothing. Used to validate the gate's field names against real payloads before enforcement is armed. |
| `claude_pretooluse_hook.py` | Enforcement leaf that imports the SAME shared gate and adds ONLY the R1–R4 rule matchers + the `permissionDecision: deny` envelope on top. |

The dependency ordering is **shared-gate (best-guess) → capture (validate /
correct) → enforce (final)**: the shared gate's best-guess field names are
authored first, the capture run confirms or corrects them against the empirical
PreToolUse payload schema, and only then is the enforcement leaf finalized on
top of the validated shared gate. No field-name knowledge is duplicated across
the two leaves — all of it lives in `pretooluse_gate.py`.

## Context gate — `Signal1 OR Signal2` (fail-open)

`pretooluse_gate.context_gate(payload)` is the single-sourced decision for
whether a call is eligible for enforcement. It returns the OR of two stateless
signals and is fail-open (False when neither fires, so calls outside a plan
context are never enforced):

- **Signal 1 — sub-agent identity.** The sub-agent identity field carries the
  `:execution-context` marker (the call runs inside a dispatched
  execution-context sub-agent). The identity value is bundle-qualified — e.g.
  `plan-marshall:execution-context-level-4` (and
  `plan-marshall:execution-context-reader-level-N` for readers) — so the gate
  matches the `:execution-context` substring, NOT a bare prefix. The field name
  and marker were confirmed against real PreToolUse payloads by the capture run.
- **Signal 2 — worktree cwd.** The working directory resolves under
  `.plan/local/worktrees/` (the call runs inside a plan worktree).

An absent Signal-1 field still lets Signal 2 satisfy the gate, and vice versa.

## Rule families

The R1–R4 matchers are enforcement-only — they live solely in the enforcement
leaf, layered on top of the shared gate, and run against the shared gate's
`tool_name(payload)` / `tool_input(payload)` accessors. On the first matching
rule the leaf emits a `permissionDecision: deny` envelope carrying a one-line
`permissionDecisionReason`; on no match it emits nothing.

| Rule | Fires on | Redirect reason (substance) |
|------|----------|-----------------------------|
| **R1 shell-construct compound** | A Bash command containing `&&`, `;`, `&`, a newline, a `for`/`while` loop, `$(...)` command substitution, or a leading `VAR=val cmd` inline env-var assignment | One command per Bash call — use separate Bash calls or dedicated tools |
| **R2 Bash file-ops** | A Bash command whose program is `cat` / `grep` / `head` / `tail` / `find` / `ls` | Use the Read/Glob/Grep tools, not Bash, for file operations |
| **R3 generated-executor edit** | An Edit/Write whose path is the generated `.plan/execute-script.py` | Regenerate the executor via `/sync-plugin-cache` + `/marshall-steward`; never edit it |
| **R4 hard-coded build** | A Bash command invoking `./pw` or a bare `mvn` / `npm` / `gradle` | Resolve build commands via `plan-marshall:manage-architecture:architecture resolve` |

## Fail-open / best-effort-no-raise contract

The whole enforcement leaf fails OPEN on every path outside a satisfied gate
plus a matched rule, so a hook bug can never block the user:

- Empty or malformed stdin → emit nothing, exit 0.
- Context gate unsatisfied → emit nothing, exit 0.
- Gate satisfied but no rule matches → emit nothing, exit 0.
- Any internal error → emit nothing, exit 0.

Only a satisfied gate plus a first-matching rule produces a deny. Every accessor
in the shared gate is best-effort and degrades to a safe default rather than
raising.

## Registration — orthogonal, on-demand, human-gated

Registration mirrors the existing terminal-title detect→confirm→install model
and is kept ORTHOGONAL to the terminal-title bundle (a project may enable one
without the other).

- **Install surface.** `project install-hook --enforcement` (in
  `claude_runtime.py`, routed through `platform_runtime.py`) idempotently adds
  ONLY the matcher-less PreToolUse enforcement entry to
  `.claude/settings.local.json`, without touching the terminal-title render /
  statusLine / env entries. It reports `enforcement_status` (`installed` /
  `already_present`).
- **Detect surface.** The `health-check --checks display` diagnostic emits a
  dedicated `PreToolUse:enforcement: present` / `MISSING` label, keyed on the
  enforcement command (not the render command), so a partial or absent
  enforcement install is diagnosable independently of the terminal-title wiring.
  The enforcement label does not gate the terminal-title `healthy` flag. The
  check inspects BOTH `.claude/settings.json` and `.claude/settings.local.json`
  (an entry in either file counts as present), matching the `hook` check and the
  fact that a hook entry can legitimately live in either file.
- **Menu surface.** The marshall-steward Configuration → Enforcement Hook action
  drives the detect→confirm→install flow; see
  [`../../marshall-steward/references/menu-enforcement-hook.md`](../../marshall-steward/references/menu-enforcement-hook.md).
- **Human-gated activation.** Writing the live `.claude/settings.local.json`
  entry hits the harness permission prompt and has session-reload activation
  latency, so it is performed by the operator (via the marshall-steward menu),
  not by an unattended task. After registration and a session reload the harness
  arms the hook.
