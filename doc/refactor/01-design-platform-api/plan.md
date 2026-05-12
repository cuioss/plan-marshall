# 01 — Design Platform API

## Objective

Design the `platform-runtime` abstraction layer: a goal-based API that routes platform-specific operations to the correct target implementation.

## Why This Cluster Exists

Skills hardcode Claude-specific paths and behaviors throughout their bodies. We need a clean boundary where skills express **what they want** and a script-based runtime layer decides **how to do it** per target.

This follows the same pattern as `tools-integration-ci`: one skill, multiple provider scripts, static routing via config.

## Compliance with Marketplace Script Standards

All `platform-runtime` scripts and operations must comply with two foundational marketplace skills:

### `tools-script-executor` Compliance

The `platform-runtime` router and all provider implementations must follow the executor pattern defined in `marketplace/bundles/plan-marshall/skills/tools-script-executor`:

- **All script calls go through `.plan/execute-script.py`**: Use notation `plan-marshall:platform-runtime:platform_runtime <operation> [args...]` for all invocations.
- **No direct script execution by path**: After the executor exists (post-bootstrap), never call `python3 /path/to/platform_runtime.py` directly.
- **Bootstrap exception**: During `marshall-steward` Steps 1-3, when the executor does not yet exist, use the glob-path bootstrap pattern. Switch to executor notation after Step 4.
- **Environment variables**: Scripts must respect `PLAN_DIR_NAME` and `PM_MARKETPLACE_ROOT` from the executor. Path construction must use these variables, not hardcoded `.plan/` or relative walks.
- **Error format**: All errors must follow the executor's standardized output: `SCRIPT_ERROR    {notation}    {exit_code}    {summary}`.
- **Exit codes**: `0` = success, `1` = invalid params, `2` = runtime error. These align with `tools-script-executor` conventions and the `manage-config` precedent.

### `ref-toon-format` Compliance

All TOON output from `platform-runtime` must be generated and parsed using the `ref-toon-format` skill:

- **Parser module**: Import and use `scripts/toon_parser.py` from the `ref-toon-format` skill. Use `parse_toon()` for reading TOON data and `serialize_toon()` for generating output.
- **No custom parsing**: Never implement ad-hoc TOON parsing logic. All internal data exchange between `platform-runtime` and calling skills must use the canonical parser.
- **TOON is internal-only**: `platform-runtime` output is consumed by other plan-marshall skills, not external APIs. Length declarations `[N]` must match actual row counts; field headers `{fields}` must match all rows.
- **Known limitations respected**: Callers must handle 2-space indentation, percentage value round-tripping, and `[N]` count mismatches per `ref-toon-format` spec.

### Verification

Before claiming this cluster complete:
- Confirm all script invocations in the design match executor notation or documented bootstrap exception.
- Confirm all TOON schemas reference `ref-toon-format` parser module, not inline string formatting.

## Output

A script-based skill (following the `tools-integration-ci` pattern):

```
platform-runtime/
├── SKILL.md                     # API contract and usage instructions
├── standards/
│   ├── contract.md              # TOON schemas for all operations
│   └── no-op-policy.md          # No-op behavior per target
└── scripts/
    ├── platform_runtime.py      # Router (reads runtime.target, dispatches)
    ├── runtime_base.py          # Abstract base class + shared TOON helpers
    ├── claude_runtime.py        # Claude Code implementation
    ├── opencode_runtime.py      # OpenCode implementation
    └── claude_hook.py          # SessionStart hook for Claude Code (sets $CLAUDE_CODE_SESSION_ID)
```

Router specification: how `runtime.target` in `marshal.json` is read and dispatched.

## API Surface

Thirteen operations, each invoked via the executor and returning TOON.

**Invocation pattern** (following the `tools-integration-ci` convention):
```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime <operation> [args...]
```

Or in skill body shorthand: `platform-runtime <operation> [args...]`

### Bootstrap Invocation (Before Executor Exists)

During first-run wizard, the executor does not yet exist. `platform-runtime` must be callable directly via glob path, following the same pattern as `bootstrap_plugin.py`. The bootstrap searches the **same root list as the post-bootstrap executor** so the discovery surface stays consistent across both phases.

**Search roots (target-aware, first match wins):**

| Target | Roots searched (in order) |
|--------|---------------------------|
| `claude` (default before `marshal.json` exists) | `~/.claude/plugins/cache/plan-marshall/*/skills/platform-runtime/scripts/platform_runtime.py` |
| `opencode` (when `--target opencode` is passed to `project initial-setup`) | `$OPENCODE_CONFIG_DIR/skills/`, `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`, `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` — looking for `plan-marshall-platform-runtime/scripts/platform_runtime.py` under each |

**Bootstrap logic** (pseudocode):

```bash
# Determine target: use --target arg if present, else read marshal.json, else default 'claude'
TARGET="${1:-$(cat .plan/marshal.json 2>/dev/null | jq -r .runtime.target)}"
TARGET="${TARGET:-claude}"

# Walk the appropriate root list and pick the first hit
case "$TARGET" in
  claude)
    PLATFORM_RUNTIME=$(ls ~/.claude/plugins/cache/plan-marshall/*/skills/platform-runtime/scripts/platform_runtime.py 2>/dev/null | head -n 1)
    ;;
  opencode)
    for root in "$OPENCODE_CONFIG_DIR/skills" .opencode/skills .claude/skills .agents/skills \
                ~/.config/opencode/skills ~/.claude/skills ~/.agents/skills; do
      [ -n "$root" ] || continue
      candidate="$root/plan-marshall-platform-runtime/scripts/platform_runtime.py"
      [ -f "$candidate" ] && PLATFORM_RUNTIME="$candidate" && break
    done
    ;;
esac

python3 "$PLATFORM_RUNTIME" <operation> [args...]
```

The OpenCode bootstrap must convert any matched location to an absolute path before invocation (same reason as the executor — bash cwd ambiguity, anomalyco/opencode#9077).

**When to use bootstrap invocation:**

| Wizard Step | Operation | Why Bootstrap |
|-------------|-----------|---------------|
| Step 1 | `project initial-setup` | Creates `.plan/` and `marshal.json`; executor does not exist |
| Step 3 | `permission configure` or `permission fix --operation ensure` | Executor permission needed before executor can run |

**Target resolution during bootstrap:**

- `project initial-setup`: Accepts `--target claude|opencode` (defaults to `claude`). Creates `marshal.json` with `runtime.target`. Since `marshal.json` does not exist yet, the target must be passed explicitly or defaulted.
- All other operations: Read `runtime.target` from `.plan/marshal.json`. If `marshal.json` is missing, returns `error` with code `marshal_not_found`.

**After Step 4 (Generate Executor):**

Switch to executor notation for all subsequent calls:
```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime <operation> [args...]
```

### `project initial-setup`

**Goal:** One-time project setup. Called by `marshall-steward` during first-time configuration.

| Argument | Description |
|----------|-------------|
| `--project-dir` | Project root (default: `.`) |
| `--target` | Platform target: `claude` or `opencode` (default: `claude`) |

**When to call:** During `marshall-steward` wizard (Step 1). Never called from phase skills.

**Claude:** Create `.plan/`, seed `marshal.json` with `runtime.target: claude`, ensure `.plan/temp/` exists. Install `SessionStart` hook in `.claude/settings.json` that captures `session_id` into `$CLAUDE_CODE_SESSION_ID` environment variable.

**OpenCode:** Same, but `runtime.target: opencode`. OpenCode does not currently expose the session id to the shell environment (tracked at upstream issue #9292; PR #9289 was closed unmerged), so no SessionStart-equivalent hook is installed. `session capture` returns `no-op` on OpenCode (see below); automatic token-usage capture is unsupported and callers fall back to manual `--total-tokens`. `.plan/execute-script.py` IS generated on OpenCode — same notation contract `{bundle}:{skill}:{script}`, but with an OpenCode-aware resolver that searches OpenCode's documented skill discovery roots plus the `$OPENCODE_CONFIG_DIR/skills/` env-var override (see Executor Resolution Per Target below).

### `session capture`

**Goal:** Read the current platform session identifier from the environment and persist it via `manage-status`.

| Argument | Description |
|----------|-------------|
| `--plan-id` | Plan identifier (required) |

**When to call:** At the start of every plan phase (init, execute, finalize, retrospective). On Claude Code this ensures `metrics capture` reads the correct session data even if the user switched terminals or started a new instance. On OpenCode the call is still made but returns `no-op` (see below).

**Precondition (Claude only):** `project initial-setup` must have been run (by `marshall-steward`) to install the `SessionStart` hook. Not applicable on OpenCode.

**Claude:** Read `$CLAUDE_CODE_SESSION_ID` environment variable (set by the `SessionStart` hook installed by `project initial-setup`). Store the value as `session_id` in `.plan/status.json` via `manage-status`. Overwrites any previous value. Returns `error` with code `hook_not_configured` if the env var is absent.

**OpenCode:** Returns `no-op` with `reason: OpenCode does not expose a platform-provided session id to the shell; tracked upstream at issue #9292` and `alternative: pass --total-tokens manually to metrics capture`. No env var is read; `session_id` remains unset in `.plan/status.json`.

### `permission configure`

**Goal:** Write a raw permission list to the target platform's settings.

| Argument | Description |
|----------|-------------|
| `--scope` | `project` or `global` |
| `--permissions` | List of patterns |

**Claude:** Patch `.claude/settings.local.json` `permissions.allow` array.
**OpenCode:** Patch `./opencode.json` or `~/.config/opencode/opencode.json`. OpenCode supports both top-level `permission` (global default) and per-agent `agent.{name}.permission` (overrides global); per-agent rules take precedence. The runtime writes whichever scope the caller selects (typically top-level for global, per-agent for agent-specific).

**Note:** This is the low-level primitive. Skills should prefer `permission analyze` and `permission fix` for hygienic permission management. When only a raw list write is needed, use `permission configure`.

### `permission analyze`

**Goal:** Read-only audit of permission configuration for hygiene, security, and completeness.

| Argument | Description |
|----------|-------------|
| `--scope` | `global`, `project`, or `both` |
| `--checks` | Comma-separated list: `redundant`, `suspicious`, `missing-steps`, `all` |
| `--marshal` | Path to `marshal.json` (required when `missing-steps` check is included) |

**Operations:**

| Check | Intent | Claude Code | OpenCode |
|-------|--------|-------------|----------|
| `redundant` | Find rules duplicated between global and project settings | Compare `~/.claude/settings.json` vs `.claude/settings.json` | Compare `~/.config/opencode/opencode.json` vs `./opencode.json` |
| `suspicious` | Detect security anti-patterns | 24 Claude-specific patterns (e.g., `Write(/tmp/**)`, `Bash(sudo:*)`) | OpenCode-specific patterns (e.g., `bash: { "*": "allow", "rm *": "ask" }` with overly broad catch-all) |
| `missing-steps` | Find `project:{skill}` steps in `marshal.json` phases 5 and 6 without matching skill permission | Checks for `Skill({skill})` or `Skill({skill}:*)` in `permissions.allow` | Checks for `"skill": { "{skill}": "allow" }` or `"skill": { "{skill}:*": "allow" }` |

**Output (TOON):**
```
status: success
checks_run[3]:
- redundant
- suspicious
- missing-steps
findings[5]:
- check: redundant
  severity: info
  details: "Bash(git:*) present in both global and project settings"
- check: suspicious
  severity: medium
  details: "bash: { '*': 'allow' } is overly broad; consider specific allow rules"
- check: missing-steps
  severity: high
  details: "project:finalize-step-plugin-doctor in phase-6-finalize steps has no matching skill permission"
summary:
  total_findings: 5
  by_severity:
    high: 1
    medium: 1
    info: 3
```

### `permission fix`

**Goal:** Apply hygienic fixes to permission configuration.

| Argument | Description |
|----------|-------------|
| `--scope` | `project` or `global` |
| `--operation` | `normalize`, `add`, `remove`, `ensure`, `consolidate` |
| `--permissions` | Permission patterns (for `add`, `remove`, `ensure`) |
| `--dry-run` | Preview changes without applying |

**Operations:**

| Operation | Intent | Claude Code | OpenCode |
|-----------|--------|-------------|----------|
| `normalize` | Deduplicate, sort, fix paths, add defaults | Normalizes `permissions.allow` array | Normalizes `permission` JSON object |
| `add` | Add a single permission rule | Appends to `permissions.allow` | Adds key to `permission.{tool}` object |
| `remove` | Remove a single permission rule | Removes from `permissions.allow` | Removes key from `permission.{tool}` object |
| `ensure` | Add missing permissions, skip existing | Idempotent array append | Idempotent object key insertion |
| `consolidate` | Merge enumerated rules into wildcards | `Read(a.log)`, `Read(b.log)` → `Read(*.log)` | Collapse object keys to wildcards |

**Defaults added by `normalize`:**

| Permission | Claude Code | OpenCode |
|------------|-------------|----------|
| Plan file access | `Edit(.plan/**)`, `Write(.plan/**)` | `agent.{name}.permission: { "edit": { ".plan/**": "allow" }, "read": { ".plan/**": "allow" } }` |
| Plugin cache access | `Read(~/.claude/plugins/cache/**)` | `permission: { "read": { "~/.config/opencode/plugins/**": "allow", "~/.config/opencode/skills/**": "allow" } }` |
| Executor pattern | `Bash(python3 .plan/execute-script.py *)` | `permission: { "bash": { "python3 .plan/execute-script.py *": "allow" } }` (OpenCode also generates `.plan/execute-script.py` — see Executor Resolution Per Target) |

### `permission ensure-wildcards`

**Goal:** Ensure all marketplace bundle wildcards exist so skills and commands are accessible without prompting.

| Argument | Description |
|----------|-------------|
| `--scope` | `project` or `global` |
| `--marketplace-dir` | Path to marketplace directory (default: `marketplace/`) |
| `--dry-run` | Preview changes without applying |

**Claude:** Scans `marketplace/.claude-plugin/marketplace.json` and `*/.claude-plugin/plugin.json`. Generates `Skill(bundle:*)` and `SlashCommand(/bundle:*)` entries.
**OpenCode:** Scans marketplace and generates `permission.skill: { "{bundle}-*": "allow" }` and `permission.command: { "{bundle}-*": "allow" }` entries. OpenCode commands ARE invocable as `/{bundle}-{skill}` per the dual-emit design — see [02 — Build System](02-build-system) "User-Invocable Skills (Dual Emission)".

### `permission ensure-steps`

**Goal:** For each `project:{skill}` step in `marshal.json` phases 5 and 6, ensure a matching skill permission exists.

| Argument | Description |
|----------|-------------|
| `--marshal` | Path to `marshal.json` |
| `--scope` | `project` or `global` |
| `--dry-run` | Preview changes without applying |

**Claude:** Adds `Skill({skill})` to `permissions.allow`.
**OpenCode:** Adds `agent.{name}.permission: { "skill": { "{skill}": "allow" } }` or `agent.{name}.permission: { "skill": { "{skill}:*": "allow" } }`.

**Usage:** Pair with `permission analyze --checks missing-steps` to close gaps surfaced by analysis.

### `permission web-analyze`

**Goal:** Read-only analysis of WebFetch / webfetch domain permissions.

| Argument | Description |
|----------|-------------|
| `--scope` | `global`, `project`, or `both` |

**Claude:** Analyzes `WebFetch(...)` entries in settings files.
**OpenCode:** Analyzes `webfetch` object in `opencode.json`.

**Output:** Categorizes domains as `universal`, `major`, `high_reach`, `suspicious`, `unknown`. Flags duplicates between global and project.

### `permission web-apply`

**Goal:** Add or remove web domain permissions.

| Argument | Description |
|----------|-------------|
| `--scope` | `project` or `global` |
| `--add` | JSON array of domains to allow |
| `--remove` | JSON array of domains to remove |
| `--dry-run` | Preview changes without applying |

**Claude:** Adds/removes `WebFetch(domain)` entries.
**OpenCode:** Modifies `agent.{name}.permission.webfetch` object.

### `session configure-display`

**Goal:** Show current plan phase in the terminal.

| Argument | Description |
|----------|-------------|
| `--type` | `terminal-title`, `status-line`, or `none` |
| `--style` | `unicode` or `ascii` |

**Claude:** Write `claude_pre_prompt.js` hook.
**OpenCode:** No-op (no hook mechanism).

### `metrics capture`

**Goal:** Record token consumption for a planning phase.

| Argument | Description |
|----------|-------------|
| `--plan-id` | Plan identifier (required) |
| `--phase` | Phase identifier (required) |
| `--total-tokens` | Token count (optional) |

**Precondition (Claude only):** `session capture` must have been called at the start of the current plan phase to populate `session_id` in `.plan/status.json` via `manage-status`. On OpenCode this precondition does not apply because `session capture` is a no-op there.

**Claude:** Read `session_id` from `.plan/status.json` via `manage-status` (set by `session capture`). Open the corresponding `.jsonl` under `~/.claude/projects/<project>/sessions/`. Sum `usage.input_tokens + usage.output_tokens` from assistant messages since the last `metrics capture` call for this phase. Returns `no-op` if `session_id` missing or transcript not found.

**OpenCode:** Returns `no-op` with `reason: automatic token capture requires a platform-provided session id, which OpenCode does not expose (issue #9292)` and `alternative: pass --total-tokens manually`. If `--total-tokens` is provided, the runtime stores it directly without consulting any session source.

### `subagent dispatch`

**Goal:** Return the correct platform-specific invocation instructions so the caller can spawn a focused subagent, or return a `no-op` if the agent cannot run on the current target.

This operation does **not** spawn the subagent itself. Both Claude Code and OpenCode require the calling AI assistant to execute the subagent via its native tool (`Task:` or `task`). `platform-runtime` resolves the platform mechanics and returns a TOON payload containing the exact parameters the caller must pass to the platform tool.

| Argument | Description |
|----------|-------------|
| `--agent` | Agent name (matches the agent markdown filename without `.md`, e.g., `phase-agent`) |
| `--prompt-file` | Path to a prompt markdown file (optional; if omitted, the agent's own body is used) |
| `--context` | JSON string of key-value pairs to inject into the prompt (optional) |

#### Platform-Specific Behavior

**Claude Code:**

1. **Agent file discovery**: Locate the agent markdown under the marketplace tree: `marketplace/bundles/*/agents/{agent-name}.md`.
2. **Parse frontmatter**: Read the `name`, `description`, and `tools:` fields.
3. **Build `Task:` payload**:
   - `description`: 3–5 words from the agent description (e.g., "Run finalize review")
   - `prompt`: The agent markdown body, with `--context` JSON merged into the top as a parameters table
   - `subagent_type`: The agent name
4. **Return TOON** with:
   ```
   status: success
   platform: claude
   invocation:
     tool: Task
     description: "..."
     prompt: "..."
     subagent_type: "{agent-name}"
   ```
5. **Caller responsibility**: The calling skill must invoke `Task:` with the returned fields.

**OpenCode:**

1. **Agent file discovery**: Same as Claude — locate `marketplace/bundles/*/agents/{agent-name}.md`.
2. **Parse frontmatter**: Read `name`, `description`, and `tools:`.
3. **Map tools to OpenCode permissions**: Transform the `tools:` list using the mapping defined in `marketplace/targets/opencode/mapping.json` (see [02 — Build System](02-build-system) for the full `tool_permissions` table).
4. **Build `task` payload**: Construct the `task` tool invocation. Note: OpenCode permissions are set in agent frontmatter (`tools:` field) or `opencode.json` (`agent.{name}.permission`), not at invocation time.
5. **Return TOON** with:
   ```
   status: success
   platform: opencode
   invocation:
     tool: task
     description: "..."
     prompt: "..."
     subagent_type: "{agent-name}"
   ```

#### No-Op Policy

`subagent dispatch` returns `no-op` only when the agent's `tools:` frontmatter contains a tool with **no OpenCode equivalent**. Examples of unsupported tools:

| Tool | Status | Reason |
|------|--------|--------|
| `SendMessage` | No-op | Agent teams feature; no OpenCode equivalent |

When an unmapped tool is detected:
```toon
status: no-op
operation: subagent dispatch
reason: "Agent {agent-name} requires unmapped tools: SendMessage, TaskCreate"
alternative: "Remove unsupported tools from agent frontmatter or inline the agent logic"
```

**Note**: `Task` and `Skill` are explicitly mapped — they are NOT Claude-only. This aligns with the cross-cutting principle: *all agents are included*.

#### Accepted Risk: `AskUserQuestion` from an OpenCode subagent

Several plan-marshall workflows include steps that prompt the user mid-dispatch (e.g.,
phase-6-finalize `branch-cleanup`'s deletion confirmation, `architecture-refresh` tier-1
mode prompt, the phase-3-outline self-modifying classification gate, the phase-4-plan
self-modifying phasing escalation, phase-2-refine Step 11 clarification questions).
On Claude Code, subagents call `AskUserQuestion` and the prompt propagates back to the
host UI; every existing finalize agent relies on this implicitly.

OpenCode's `task` tool semantics around child-tool re-prompting are not documented in
this repo and have not been validated in a live OpenCode session. **This is accepted as
a known risk for cluster 01**: the cluster ships assuming OpenCode subagents can prompt
the user via the platform's native `ask` (or equivalent) tool. If validation in cluster
04 (Validate and Document) surfaces that OpenCode subagents cannot prompt, the affected
step kinds will need an `inline_only: true` flag on their dispatch — but that retrofit
is a small contract addition, not a redesign.

This risk is **not** a blocker for cluster 01 design or implementation; it is documented
here for the cluster-04 validation pass to verify.

#### When `subagent dispatch` Returns `no-op`

The calling skill has three options:

| Option | When to use |
|--------|-------------|
| **Inline the agent logic** | Copy the agent's markdown body into the caller's own prompt and execute directly. Best for one-off tasks when the agent has unmapped tools. |
| **Convert to script** | Extract the agent's workflow into a `scripts/*.py` file under a skill, then call it via `python3 .plan/execute-script.py ...`. Best for reusable logic that cannot use subagents. |
| **Skip the step** | If the agent is optional (e.g., coverage analysis), proceed without it and note the omission in `metrics capture`. |

#### Examples

**Example 1: Dispatch compatible agent on Claude Code**

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  subagent dispatch \
  --agent "detect-change-type-agent" \
  --context '{"plan_id": "my-plan", "files": ["src/Foo.java"]}'
```

Output:
```toon
status: success
platform: claude
invocation:
  tool: Task
  description: "Detect change type"
  prompt: "...agent body with context merged..."
  subagent_type: "detect-change-type-agent"
```

Caller then executes:
```
Task: description="Detect change type" prompt="..." subagent_type="detect-change-type-agent"
```

**Example 2: Dispatch agent with Task/Skill on OpenCode (all tools mapped)**

`phase-agent` uses `Task` and `Skill` in its `tools:` frontmatter. Both are mapped:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  subagent dispatch \
  --agent "phase-agent" \
  --context '{"skill": "plan-marshall:phase-1-init"}'
```

Output:
```toon
status: success
platform: opencode
invocation:
  tool: task
  description: "Run phase init"
  prompt: "...agent body with context merged..."
  subagent_type: "phase-agent"
```

Note: OpenCode permissions are set in agent frontmatter (`tools:` field) or `opencode.json` (`agent.{name}.permission`), not at `task` invocation time. The caller uses the invocation parameters to spawn the subagent via the `task` tool.

**Example 3: Dispatch agent with unmapped tools on either platform**

Hypothetical future agent using `SendMessage` (Claude Code agent teams feature, no OpenCode equivalent):

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  subagent dispatch \
  --agent "team-coordinator-agent"
```

Output:
```toon
status: no-op
operation: subagent dispatch
reason: "Agent team-coordinator-agent requires unmapped tools: SendMessage"
alternative: "Remove unsupported tools from agent frontmatter or inline the agent logic"
```

### `health-check`

**Goal:** Verify platform integration.

| Argument | Description |
|----------|-------------|
| `--checks` | `all`, `permissions`, `display`, `mcp-diagnostics` |

**Claude:** Check settings, hooks, MCP diagnostics.
**OpenCode:** Check `opencode.json`, `agent.{name}.permission` or global tool permissions.

## Router Design

1. Script reads `.plan/marshal.json`
2. Extracts `runtime.target` (defaults to `claude`)
3. Looks up target class in registry: `{'claude': ClaudeRuntime, 'opencode': OpenCodeRuntime}`
4. Dispatches to implementation
5. Returns TOON

Registry must be extensible — adding a new target means adding a new class + registration entry.

## Executor Resolution Per Target

Skill bodies invoke scripts via the canonical notation `python3 .plan/execute-script.py {bundle}:{skill}:{script} [subcommand] [args...]`. This notation is **target-portable** — the body never changes between targets. The only thing that changes is the resolver embedded in the generated `.plan/execute-script.py`.

`tools-script-executor` regenerates the executor with a target-aware resolver when `runtime.target` in `marshal.json` changes. The two resolvers today:

| Target | Skill discovery roots (first match wins) | Notation → path mapping |
|--------|------------------------------------------|-------------------------|
| `claude` | `~/.claude/plugins/cache/plan-marshall/*/skills/{skill}/scripts/{script}.py` | `{bundle}:{skill}:{script}` → first `{skill}/scripts/{script}.py` under the plugin cache |
| `opencode` | `$OPENCODE_CONFIG_DIR/skills/`, `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`, `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | `{bundle}:{skill}:{script}` → first `{bundle}-{skill}/scripts/{script}.py` (note: dash-namespaced directory name to match dual-emit layout) |

**Why absolute paths:** the OpenCode resolver always converts the matched location to an absolute path before invoking. OpenCode's bash-tool cwd is not guaranteed to be the project root (anomalyco/opencode#9077). Resolving to an absolute path before exec sidesteps cwd ambiguity entirely.

**Bootstrap exception (unchanged):** during `marshall-steward` Steps 1–3 the executor does not yet exist, so direct glob-path invocation is used per the Bootstrap Invocation section above. Step 4 generates the target-appropriate executor; thereafter all calls go through the executor.

**No body rewriting:** the OpenCode emitter does **not** transform `python3 .plan/execute-script.py …` lines. The notation is identical on both targets; only the resolver behind it differs. This keeps every workflow body portable.

## TOON Contract

Every operation returns:

```toon
status: success | error | no-op
operation: <name>
result: <any>        (success only)
error: <string>      (error only)
message: <string>    (error only)
reason: <string>     (no-op only)
alternative: <string> (no-op only)
```

See `standards/contract.md` for per-operation schemas.

## Error Codes

| Code | Meaning |
|------|---------|
| invalid_scope | scope not project/global |
| invalid_check | permission analyze --checks contains unknown check name |
| marshal_not_found | .plan/marshal.json missing (required for missing-steps check) |
| prompt_not_found | subagent dispatch prompt file missing |
| unknown_target | runtime.target not in registry |
| hook_not_configured | SessionStart hook missing; env var not set (run marshall-steward to run project initial-setup) |

## No-Op Specification

When a target returns `no-op`:
- Status is `no-op`, not `error`
- `reason` explains why
- `alternative` suggests what the user can do
- The calling skill must continue (not fail)

Examples:

```toon
status: no-op
operation: session configure-display
reason: OpenCode has no plugin-driven status-line hook (issue anomalyco/opencode#8619)
alternative: Use --type none, or use OpenCode's built-in /statusline TUI command for an interactive status line
```

```toon
status: no-op
operation: metrics capture
reason: Session ID found but transcript/DB query returned no usage data for this phase
alternative: Pass --total-tokens manually
```

## Session Hook Setup

**One-time configuration per project (Claude only).**

On Claude, `project initial-setup` installs a `SessionStart` hook that captures the platform's session identifier and makes it available as an environment variable to all subsequent tool calls. On OpenCode no hook is installed (see "OpenCode Hook" below).

### Claude Code Hook

Installed to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .plan/execute-script.py plan-marshall:platform-runtime:claude_hook",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

The hook script reads `session_id` from stdin JSON and writes it to `$CLAUDE_ENV_FILE` as `$CLAUDE_CODE_SESSION_ID`.

### OpenCode Hook

OpenCode does not currently expose a platform-provided session id to the shell environment. Upstream issue #9292 tracks the request; PR #9289 attempting to land it was closed unmerged. `project initial-setup` skips hook installation on OpenCode and `session capture` returns `no-op`.

### Why Hooks Are Required

Neither Claude Code nor OpenCode exposes a reliable programmatic API to discover the "current session" from within a running script. The only accurate channel is the platform's own hook system, which passes session metadata at session start. Heuristics like "most recent transcript file" fail when multiple sessions run concurrently.

### Fallback

- **Claude:** if `project initial-setup` has not been run, the hook is missing and the env var is unset. `session capture` returns `error` with code `hook_not_configured`. The calling skill can either run `marshall-steward` (which calls `project initial-setup`) to install the hook, or accept manual `--total-tokens` input and skip automatic capture.
- **OpenCode:** no hook is expected; `session capture` always returns `no-op` with the documented `reason`/`alternative`. The calling skill must continue and accept manual `--total-tokens` input where token capture is needed.

## What Stays Out

These do NOT belong in platform-runtime:

| Concern | Belongs To |
|---------|-----------|
| CI/PR operations | `tools-integration-ci` |
| Plan state (tasks, status) | `manage-status`, `manage-tasks` |
| Architecture data | `manage-architecture` |
| Metrics storage/analysis | `manage-metrics` |
| Executor regeneration | `tools-script-executor` |
| Bundle distribution | `marketplace/targets/` generator + CI |

## Boundary Test

Ask: "Would this operation work identically on both Claude and OpenCode?"
- If yes → plan-marshall internal skill
- If no → platform-runtime

## Verification

This cluster is complete when:
1. API contract document exists and covers all 13 operations
2. TOON schemas defined for success, error, and no-op paths
3. Router specification documented
4. Boundary rules clear enough that a new skill author knows where to put things

## Dependencies

None. This is the foundational cluster. All other clusters depend on it.
