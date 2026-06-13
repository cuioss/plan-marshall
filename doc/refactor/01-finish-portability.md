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
| `phase-5-execute` token capture | **Gap** — no `session capture` / `metrics capture` / `platform_runtime` reference in the body; still its own token-extraction path. |
| `plan-retrospective` token capture | **Gap** — same as phase-5. |
| `marshall-steward` bootstrap (`bootstrap_plugin.py`) | **Gap** — `detect_plugin_root()` hardcodes `~/.claude/plugins/cache/`; no OpenCode-root discovery, no `runtime.target` read. |
| `tools-permission-doctor` / `tools-permission-fix` / `workflow-permission-web` | **Likely gap** — no `platform-runtime permission …` delegation found in their scripts; settings I/O appears direct. Needs an explicit audit. |
| `tools-input-validation` session_id rule | **Needs audit** — confirm whether `session_id` validation branches on `runtime.target` (Claude UUID vs OpenCode shape) or still assumes UUID. |
| `marshal.json` `runtime.target` field | **Needs confirm** — `project initial-setup` accepts `--target`; confirm the field is actually written into the init-time `marshal.json` and defaults to `claude`. |

## Tasks

Each task: audit → migrate the call site to `platform-runtime` → test on both targets.

1. **`phase-5-execute` — capture via runtime.** Replace the local token-extraction with
   `session capture` at phase start and `platform-runtime metrics capture --phase
   5-execute`. On Claude the runtime reads the stored `session_id`; on OpenCode it
   returns `no-op` and the phase proceeds with manual `--total-tokens`.

2. **`plan-retrospective` — capture via runtime.** Same treatment: `session capture` at
   start, `metrics capture --phase retrospective`; replace any transcript-walking with
   the runtime call; permission-prompt analysis routes through `permission analyze
   --checks suspicious`.

3. **`bootstrap_plugin.py` — multi-platform path resolution.** Teach
   `detect_plugin_root()` to read `runtime.target` (arg → `marshal.json` → default
   `claude`) and walk the matching root list: the single Claude cache root, or the seven
   OpenCode discovery roots (`$OPENCODE_CONFIG_DIR/skills`, `.opencode/skills`,
   `.claude/skills`, `.agents/skills`, `~/.config/opencode/skills`, `~/.claude/skills`,
   `~/.agents/skills`). Convert the match to an absolute path before invoking
   (anomalyco/opencode#9077). This mirrors the resolver already shipped in
   `generate_executor.py`.

4. **Permission tools — delegate to the runtime.** Audit `tools-permission-doctor`,
   `tools-permission-fix`, and `workflow-permission-web`. Where they read/write
   `.claude/settings*.json` directly, replace with `platform-runtime permission analyze`
   / `permission fix` / `permission web-analyze` / `permission web-apply`. The Claude-
   specific anti-pattern lists and settings shapes live in `claude_runtime.py`, not in
   the skill body.

5. **`tools-input-validation` — target-specific `session_id`.** Branch the `session_id`
   rule on `runtime.target`: Claude validates the UUID shape; OpenCode validates its
   documented shape (or accepts an opaque string if none is documented).

6. **Confirm the `marshal.json` template.** Verify a fresh `project initial-setup` writes
   `runtime.target` (defaulting to `claude`, `opencode` when `--target opencode`). Add it
   to the template if missing.

7. **Final audit grep.** Grep `marketplace/bundles/*/skills/*/SKILL.md` (excluding
   `skills/platform-runtime/**`) for remaining behavioural `.claude/` / `~/.claude`
   references — writes, reads, hook installation. Each remaining hit must be a
   `platform-runtime` call site or a `references/{topic}.md` pointer.

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
