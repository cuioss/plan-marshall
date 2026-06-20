# 01 — Finish portability gaps

## Objective

Route the last remaining Claude-specific call sites through `platform-runtime` so that
nothing in a general skill body bypasses the abstraction before the runtime is validated
on OpenCode (document [02](02-validate-opencode-runtime.md)).

The `platform-runtime` skill itself is the sanctioned home for per-platform code and is
**out of scope** for any audit here — its `claude_runtime.py` / `claude_hook.py` /
`opencode_runtime.py` contain `.claude/` paths and hook strings by design.

## Current state (verified against the tree)

| Item | State |
|------|-------|
| `platform-runtime` API (15 ops, both runtimes) | **Done** — `opencode_runtime.py` implements every operation. |
| Target-aware executor (`tools-script-executor`) | **Done** — Claude-cache resolver + OpenCode 7-root resolver, switched on `runtime.target`. |
| `phase-1-init`, `phase-6-finalize` session handling | **Done** — both reference the `session capture` contract. |
| `phase-5-execute` token capture | **Done** — `session capture` at phase start (line 985), `metrics capture --phase 5-execute` at phase transition (line 1112). |
| `plan-retrospective` token capture | **Done** — `session capture` at start (line 78), `metrics capture --phase retrospective` before mode-specific termination (line 306). |
| `marshall-steward` bootstrap (`bootstrap_plugin.py`) | **Done** — `read_runtime_target()` reads from arg/marshal.json/default; `_detect_opencode_root()` walks 7 roots; `--target` CLI flag added. |
| `tools-permission-doctor` / `tools-permission-fix` / `workflow-permission-web` | **Partial** — SKILL.md guidance updated (prose note to prefer `platform-runtime permission`), but scripts (`permission_common.py`) still hardcode `.claude/settings.json` paths. OpenCode runtime stubs return no-op. |
| `tools-input-validation` session_id rule | **Needs audit** — confirm whether `session_id` validation branches on `runtime.target` (Claude UUID vs OpenCode shape) or still assumes UUID. |
| `marshal.json` `runtime.target` field | **Done** — `project initial-setup --target opencode` writes `"runtime": {"target": "opencode"}`. Confirmed in validation session. |

## Tasks

Each task: audit → migrate the call site to `platform-runtime` → test on both targets.

1. **`phase-5-execute` — capture via runtime.**
   **Status: DONE** — `session capture` at phase start, `metrics capture --phase 5-execute` at phase transition.

2. **`plan-retrospective` — capture via runtime.**
   **Status: DONE** — `session capture` at start, `metrics capture --phase retrospective` before termination.

3. **`bootstrap_plugin.py` — multi-platform path resolution.**
   **Status: DONE** — `read_runtime_target()`, `_detect_opencode_root()` (7-root walk), `--target` CLI arg.

4. **Permission tools — delegate to the runtime.** Audit `tools-permission-doctor`,
   `tools-permission-fix`, and `workflow-permission-web`. Where they read/write
   `.claude/settings*.json` directly, replace with `platform-runtime permission analyze`
   / `permission fix` / `permission web-analyze` / `permission web-apply`. The Claude-
   specific anti-pattern lists and settings shapes live in `claude_runtime.py`, not in
   the skill body.
   **Status: PARTIAL** — SKILL.md guidance updated (2026-06-19). Scripts still hardcode
   `.claude/` paths. OpenCode runtime stubs return no-op. Full migration remains.

5. **`tools-input-validation` — target-specific `session_id`.** Branch the `session_id`
   rule on `runtime.target`: Claude validates the UUID shape; OpenCode validates its
   documented shape (or accepts an opaque string if none is documented).
   **Status: OPEN**

6. **Confirm the `marshal.json` template.** Verify a fresh `project initial-setup` writes
   `runtime.target` (defaulting to `claude`, `opencode` when `--target opencode`). Add it
   to the template if missing.
   **Status: DONE** — Confirmed in validation session. `project initial-setup --target opencode`
   writes `"target": "opencode"` into marshal.json.

7. **Final audit grep.** Grep `marketplace/bundles/*/skills/*/SKILL.md` (excluding
   `skills/platform-runtime/**`) for remaining behavioural `.claude/` / `~/.claude`
   references — writes, reads, hook installation. Each remaining hit must be a
   `platform-runtime` call site or a `references/{topic}.md` pointer.
   **Status: OPEN**

## Additional findings from OpenCode validation (2026-06-19)

- **Body transformer not wired**: `OpenCodeTarget.generate()` did not pass `body_transformer`
  to `emit_bundles`. All `Skill:` directives survived raw. Fixed in
  `marketplace/targets/opencode/target.py`.
- **AGENTS.md leaked into distributed output**: `opencode.json` hardcoded
  `instructions: ["AGENTS.md"]` but the emitted tree is a distributable plugin, not a
  project root. Removed — instructions are the downstream project's concern.
- **Multiple doc/refactor documents stale**: Updated to reflect completion status.

## Acceptance

- No behavioural `.claude/` reference remains in a general skill body (platform-runtime
  excluded).
- `phase-5-execute` and `plan-retrospective` capture tokens through `platform-runtime`.
- `bootstrap_plugin.py` resolves on both targets.
- Permission tools delegate all settings I/O to the runtime.
- `marshal.json` carries `runtime.target`.
- `verify` passes on all bundles (Claude canary — no regression).

## Dependencies

None beyond the landed baseline. This is the precondition for [02](02-validate-opencode-runtime.md).
