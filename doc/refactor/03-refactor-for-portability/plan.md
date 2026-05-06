# 03 — Refactor for Portability

## Objective

Remove Claude-specific path leakage from skills and prepare them to use the `platform-runtime` script skill.

All calls go through the executor: `python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime <operation> [args...]`

## Why This Cluster Exists

Skills hardcode `.claude/settings.local.json`, `~/.claude/plugins/cache/`, and Claude-specific hook instructions. These must be abstracted behind `platform-runtime` before multi-target generation is meaningful.

## Scope

All 10 bundles, but with priority:
1. **plan-marshall** — highest priority (contains the runtime, wizard, and phase skills)
2. **Other 9 bundles** — audit only; they likely have no Claude-specific content in bodies

## Output

- Updated skill bodies that use `platform-runtime` goal-based calls
- `runtime.target` field in `marshal.json` template
- `marshall-steward` wizard rewritten for platform-agnostic instructions
- OpenCode adapter logic migrated into target engine (see 02)

## Audit Checklist

Search all skill bodies for:

| Pattern | Violation | Fix |
|---------|-----------|-----|
| `.claude/settings.local.json` | Hardcoded Claude settings path | Use `platform-runtime permission configure` |
| `~/.claude/settings.json` | Hardcoded global Claude settings path | Use `platform-runtime permission-*` with `--scope global` |
| `claude_pre_prompt.js` | Hardcoded hook filename | Use `platform-runtime session configure-display` |
| `<usage>` tag parsing in skill body | Hardcodes Claude-specific transcript parsing | Use `platform-runtime metrics capture` (runtime reads stored session_id) |
| `Task:` tool in body | Claude-only subagent dispatch | Use `platform-runtime subagent dispatch` |
| `permissions.allow` array manipulation | Claude-specific permission format | Use `platform-runtime permission fix` |
| `WebFetch(...)` string parsing | Claude-specific web permission format | Use `platform-runtime permission-web-*` |

### Skills Requiring Body Changes (plan-marshall)

| Skill | From | To |
|-------|------|----|
| `phase-1-init` | None (new call needed) | `session capture` at start (SessionStart hook installed by `project initial-setup`, called once during `marshall-steward`) |
| `phase-5-execute` | Extract `total_tokens` from `<usage>` tag | Add `session capture` at start; use `metrics capture --phase 5-execute` |
| `phase-6-finalize` | `session_id` = Claude UUID | Add `session capture` at start; use `metrics capture --phase 6-finalize` |
| `plan-retrospective` | Transcript analysis | Add `session capture` at start; use `metrics capture --phase retrospective` |
| `marshall-steward` | Write hooks to `.claude/settings.local.json` | `platform-runtime session configure-display` |
| `marshall-steward` | Patch `.claude/settings.local.json` permissions | `platform-runtime permission configure` |
| `tools-permission-doctor` | Read `~/.claude/settings.json`, `.claude/settings.json`; Claude-specific anti-patterns | `platform-runtime permission analyze --checks <checks>` |
| `tools-permission-fix` | Write to `~/.claude/settings.json`, `.claude/settings.json`; `ensure-executor` / `cleanup-scripts` / `migrate-executor` are Claude-specific executor operations | `platform-runtime permission fix --operation <op>`; `ensure-executor`/`cleanup-scripts`/`migrate-executor` return `no-op` on OpenCode |
| `workflow-permission-web` | Read `WebFetch(...)` strings from `.claude/settings*.json` | `platform-runtime permission web-analyze --scope <scope>`; `platform-runtime permission web-apply --add/--remove` |
| `tools-script-executor` | Generates `.plan/execute-script.py` using `~/.claude/plugins/cache/` paths; bootstrap reads `~/.claude/plugins/cache/` | Target engine handles bundle sync to target-specific plugin directory (`.claude/` or `.opencode/`). Bootstrap resolves path via `platform-runtime` or target-configurable path. |
| `tools-file-ops` | Worktree paths under `.claude/worktrees/` hardcoded | Use `marshal.json` `worktree.path` (target-configurable, default `.claude/worktrees/` for Claude, `.opencode/worktrees/` for OpenCode) |
| `manage-worktree` | Creates worktrees under `.claude/worktrees/{plan_id}/` | Use `marshal.json` `worktree.path` prefix; do not hardcode `.claude/` segment |
| `tools-input-validation` | Validates `session_id` as "Claude Code UUID-shape token" | Target-specific validation: Claude UUID format vs OpenCode session format |
| `plan-retrospective` | Permission prompt analysis references `.claude/settings.json` | Use `platform-runtime permission analyze --checks suspicious` to diagnose prompts; target-agnostic report generation |

### Commands Requiring Changes

| Command | From | To |
|---------|------|----|
| `tools-fix-intellij-diagnostics` | `mcp__ide__getDiagnostics` tool call | `platform-runtime health-check --checks mcp-diagnostics` |

### Skills Unaffected (remaining skills, 9 agents, 1 command)

No body changes needed. These are already platform-agnostic.

**Note:** The following skills require body changes (see table above): `phase-1-init`, `phase-5-execute`, `phase-6-finalize`, `plan-retrospective`, `marshall-steward`, `tools-permission-doctor`, `tools-permission-fix`, `workflow-permission-web`, `tools-script-executor`, `tools-file-ops`, `manage-worktree`, `tools-input-validation`.

## marshal.json Template

Add `runtime.target` to the template used by `phase-1-init`:

```json
{
  "runtime": {
    "target": "claude"
  }
}
```

Defaults to `claude` for backward compatibility. OpenCode users can override.

## marshall-steward Wizard Rewrite

The wizard guides first-time setup. Rewrite each step to use goal-based calls:

| Step | From | To | Invocation |
|------|------|----|------------|
| Step 1 (Init) | Manual `.plan/` setup | `project initial-setup --project-dir .` | Bootstrap (direct) — executor does not exist |
| Step 3 (Permissions) | Patch `.claude/settings.local.json` | `permission fix --operation ensure --permissions "..." --scope project` | Bootstrap (direct) — executor does not exist yet |
| Step 4 (Bundle wildcards) | None (manual) | `permission ensure-wildcards --scope project --marketplace-dir marketplace/` | Executor — available after Step 4 generates it |
| Step 5 (Bundles) | Search plugin cache | Run target generator for the active target (see 02) | Executor |
| Step 13 (Terminal) | Write Claude hooks | `session configure-display --type terminal-title --style unicode` | Executor |

## Phase Skills Rewrite

Every phase skill that starts a plan session must call `session capture` before any work:

| Skill | Call Location |
|-------|--------------|
| `phase-1-init` | At start, before creating plan documents |
| `phase-5-execute` | At start, before executing the plan |
| `phase-6-finalize` | At start, before finalizing |
| `plan-retrospective` | At start, before retrospective analysis |

This ensures `session_id` in `.plan/status.json` (managed via `manage-status`) always points to the current platform session.

## Bootstrap Exception

The `marshall-steward` wizard uses a bootstrap pattern: it calls scripts directly (`python3 "$SCRIPT"`) outside the executor. This is a documented exception.

**Problem:** On OpenCode, `bootstrap_plugin.py` needs to find the correct script path without relying on `~/.claude/plugins/cache/`.

**Solution:** Extend `bootstrap_plugin.py` to:
1. Check `runtime.target` from `marshal.json` (if exists)
2. Search multiple locations: plugin cache, `.opencode/skills/`, local `marketplace/bundles/`
3. Use first match

This is a script change, not a skill body change.

## Other 9 Bundles

Audit for Claude-specific content:

| Bundle | Expected Result |
|--------|----------------|
| pm-dev-java | Likely clean (Java standards) |
| pm-dev-java-cui | Likely clean |
| pm-dev-frontend | Likely clean |
| pm-dev-frontend-cui | Likely clean |
| pm-dev-oci | Likely clean |
| pm-dev-python | Likely clean |
| pm-documents | Likely clean |
| pm-plugin-development | Check for plugin path references |
| pm-requirements | Likely clean |

If any bundle contains `.claude/` references in skill bodies, flag for update.

## Adapter Migration

`marketplace/adapters/opencode_adapter.py` must be migrated into the target engine. See [02 — Build System](02-build-system) for the full migration steps and architecture.

## Verification

This cluster is complete when:
1. No `.claude/`, `~/.claude`, or Claude-specific tool names remain in plan-marshall skill bodies
2. `marshall-steward` uses goal-based calls for all platform-specific operations
3. `marshal.json` template includes `runtime.target`
4. `project initial-setup` installs the `SessionStart` hook for session capture
5. `bootstrap_plugin.py` handles multi-platform path resolution
6. `marketplace/adapters/` retired (logic in `marketplace/targets/`)
7. `tools-permission-doctor`, `tools-permission-fix`, and `workflow-permission-web` delegate all settings file I/O to `platform-runtime` permission operations
8. Executor-specific operations (`ensure-executor`, `cleanup-scripts`, `migrate-executor`) return `no-op` on OpenCode target
9. `./pw verify` passes

## Dependencies

- `01-design-platform-api` — must know the API surface to refactor skills correctly
- `02-build-system` — adapter migration depends on the target framework
- `05-distribution` — not a direct dependency, but distribution design informs how artifacts are structured
