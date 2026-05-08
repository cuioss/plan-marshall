# 02 — Build System

## Objective

Create the build-time target generator framework that reads source bundles (Claude Code format) and emits platform-specific artifacts.

## Scope

This cluster covers:
- Target generator framework (`marketplace/targets/`)
- Drift detection for Claude Code source format
- OpenCode format emitter
- Future target support (Cursor, etc.)

This does NOT cover:
- CI/CD pipeline (see [05 — Distribution](05-distribution))
- Release artifact hosting (see [05 — Distribution](05-distribution))
- Local deployment to Claude Code plugin cache (already handled by `sync-plugin-cache` skill)
- Local deployment to OpenCode (see [06 — Developer Workflow](06-developer-workflow))
- End-user installation (see [05 — Distribution](05-distribution))

## Why This Cluster Exists

An ad-hoc adapter (`marketplace/adapters/opencode_adapter.py`) generates OpenCode output. We need a proper, extensible target engine that supports multiple output formats from a single source of truth.

## Output

- `marketplace/targets/` directory with framework code
- CLI entry point for local and CI use
- Retire `marketplace/adapters/` (logic migrated into target engine)

## Architecture

```
marketplace/targets/
├── base.py                  # TargetBase abstract class
├── generate.py              # CLI entry point
├── opencode/
│   ├── target.py            # OpenCode target implementation (OpenCodeTarget class)
│   ├── emitter.py           # OpenCode emitter
│   ├── frontmatter.py       # Frontmatter transform engine
│   ├── body-transforms.py   # Mechanical body-text transforms (Skill: rewrite, slash rewrite)
│   ├── mapping.json         # Tool + model + layout mappings
│   ├── frontmatter-rules.json  # Frontmatter transform rules
│   ├── transforms.md        # Spec for the mechanical body-text transforms
│   └── templates/           # Body-text templates the emitter substitutes into
│       └── user-invocable-command.md  # Wrapper command body for user-invocable skills
└── claude/
    ├── target.py             # Claude target implementation (ClaudeTarget class)
    └── drift.py             # Drift detection engine
```

### TargetBase Contract

Every target implements:

```python
class TargetBase(ABC):
    @property
    def name(self) -> str: ...
    def generate(self, marketplace_dir: Path, output_dir: Path, bundles: list[str] | None) -> list[Path]: ...
    def supports_agents(self) -> bool: ...
    def supports_commands(self) -> bool: ...
    @property
    def config_dir(self) -> Path: ...
```

**Config-driven:** Each target reads mapping rules from JSON files in its own `config_dir` subdirectory. No hardcoded transforms.

### Registry

```python
TARGET_REGISTRY = {
    'claude': ClaudeTarget,
    'opencode': OpenCodeTarget,
}
```

Adding a target: implement `TargetBase`, register in `TARGET_REGISTRY`.

## Claude Target (Dual-Mode: Verbatim Mirror + Always-Generate plugin.json)

**Behavior:** Dual-mode generator selected by whether the caller passes `--output`:

1. **Validate mode** (`--output` omitted): regenerate `plugin.json` for every bundle in-memory and diff against the committed `marketplace/bundles/{bundle}/.claude-plugin/plugin.json`. Exit 0 on match, exit 2 with a TOON drift report on mismatch.
2. **Emit mode** (`--output` provided): walk `marketplace/bundles/{bundle}/**`, copy bundle content byte-for-byte into `{output}/{bundle}/`, AND always (re)generate `{output}/{bundle}/.claude-plugin/plugin.json` from source frontmatter. After emit, run the same equality check against the committed `plugin.json` so drift is surfaced in the same return.

**Always-generate semantics:** `plugin_json_gen.py` scans `agents/*.md`, `commands/*.md`, and `skills/*/SKILL.md` to produce a deterministic, sorted-array `plugin.json`. Top-level fields (`name`, `version`, `description`, `author`, `license`, `homepage`, `repository`, `keywords`) are read from the existing committed `plugin.json` and pass through unchanged — only the component arrays come from the frontmatter scan. The output is byte-stable across runs so the equality check produces stable diffs.

**Equality check** (single mechanism — no separate orphan/missing partition logic): regenerate in-memory, compare to the committed file, surface mismatches as TOON. The check drives both the standalone validation mode and the CI/PR equality gate. If someone adds a skill but forgets to update `plugin.json`, or vice-versa, the equality check catches it on the next CI run.

**Output:** TOON return with `status`, `emitted_count`, `plugin_json_diff_count`, `equality_check_result`. Exit 0 on success, exit 2 on equality drift or any other failure.

**Future variant emission.** The door stays open for per-target frontmatter layering (e.g., variant `plugin.json` content for staging vs production). Extending `plugin_json_gen.py` to layer target-specific fields does not change the equality-check contract — the regenerator remains deterministic, and the committed `plugin.json` continues to be the equality-baseline.

## OpenCode Target (Format Emitter)

**Behavior:** Full emitter. Translates Claude Code source format into the layout expected by the `opencode-marketplace` CLI (singular subdirectory names — see [05 — Distribution](05-distribution)) inside the output directory (default: `target/opencode/`):

```
target/opencode/
├── skill/
│   └── {bundle}-{skill}/
│       └── SKILL.md
├── agent/
│   └── {agent}.md
├── command/
│   └── {command}.md
└── opencode.json
```

**Singular vs plural directory names.** OpenCode's native runtime discovery uses plural directories (e.g. `~/.config/opencode/skills/`); the `opencode-marketplace` CLI's expected source-repo layout uses singular (`skill/`, `agent/`, `command/`). The emitter writes the singular form because the primary distribution path is `opencode-marketplace install`. Workflows that need the plural form (`sync-opencode` deployment to `~/.config/opencode/`, direct `OPENCODE_CONFIG_DIR` usage) rename singular → plural during deployment — see [06 — Developer Workflow](06-developer-workflow).

**Output directory is configurable.** The CLI accepts `--output <dir>` (default: `target/opencode/`). This is a **build output directory**, not `.opencode/` at the project root — placing generated artifacts at `.opencode/skills/` would conflict with committed project-local skills (see [06 — Developer Workflow](06-developer-workflow)).

This is a **build target** (like a compiler backend), not a deployment mechanism. The generated output directory is then copied to the user's OpenCode config directory or packaged for distribution via the pipeline in [05 — Distribution](05-distribution).

### Transformations

All transformations are driven by configuration files, not hardcoded logic. This allows mapping updates without code changes.

#### Configuration: `marketplace/targets/opencode/mapping.json`

Tool and model mappings (see [01 — Design Platform API](01-design-platform-api) for the full tool mapping table):

```json
{
  "tool_permissions": {
    "Read": "read",
    "Write": "edit",
    "Edit": "edit",
    "Glob": "glob",
    "Grep": "grep",
    "Bash": "bash",
    "WebFetch": "webfetch",
    "WebSearch": "websearch",
    "AskUserQuestion": "question",
    "Task": "task",
    "Skill": "skill",
    "NotebookEdit": "edit",
    "TaskCreate": "todowrite",
    "TaskGet": "todoread",
    "TaskList": "todoread"
  },
  "model_map": {
    "opus": "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001"
  }
}
```

**Note:** The generator adds the `anthropic/` provider prefix when writing `opencode.json`, so model IDs here are without prefix.

#### Configuration: `marketplace/targets/opencode/frontmatter-rules.json`

Owns the frontmatter-shape rules (which fields are required, which are optional). Loads `tool_permissions` and `model_map` from `mapping.json` at runtime — `mapping.json` owns the dictionaries; `frontmatter-rules.json` owns the validation contract. No field is duplicated across the two files.

```json
{
  "required_fields": ["description"],
  "optional_fields": ["model", "mode"]
}
```

### Model Mapping Rationale

Claude Code aliases (`opus`, `sonnet`, `haiku`) resolve to the latest version. OpenCode requires explicit model IDs. The generator maps to the current available version to preserve the skill author's intent:

- `opus` → `claude-opus-4-7` (deep reasoning, reliable rule following)
- `sonnet` → `claude-sonnet-4-6` (daily coding)
- `haiku` → `claude-haiku-4-5-20251001` (simple tasks)

**Note:** OpenCode provider prefix (`anthropic/`) is added by the config generator, not included in the model ID mapping.

**No forced downgrades.** If a skill specifies `opus`, the OpenCode output preserves that requirement. The generator maps to the latest stable version per MODEL_MAP.

### Limitation: Instruction Following

Research shows OpenCode's instruction injection mechanism differs from Claude Code's:

- **Claude Code:** `CLAUDE.md` is injected as a "system reminder" that persists through compaction and is re-injected into context throughout the session
- **OpenCode:** `AGENTS.md` is loaded once at session start. As context compacts, instructions may be lost
- **Known issue (#8892):** Anthropic models in OpenCode sometimes ignore `instructions` array content entirely (open upstream)
- **Known issue (#11441):** OpenCode's Plan agent does not enforce plan rules architecturally — it relies on the LLM to respect them voluntarily

**Temperature does not solve this.** OpenCode supports `temperature: 0.1` for more deterministic output, but this affects creativity, not instruction comprehension. A model that cannot understand complex rules at `temperature=0.7` will not suddenly understand them at `temperature=0.1`.

**Practical implication:** For skills with complex multi-step workflows (like plan-marshall's 54 skills), `opus` is strongly recommended. Mapping `opus` to `sonnet` to save costs will degrade reliability.

### Agent Mapping

Agents with `Task` or `Skill` in their `tools:` frontmatter are **not** Claude-only. OpenCode has equivalent `task` and `skill` tools. See [01 — Design Platform API](01-design-platform-api) for the full tool mapping table.

**Implementation note:** Permissions are set in agent frontmatter (`tools:` field) or `opencode.json` (`agent.{name}.permission`), not at `task` invocation time. The `subagent dispatch` operation returns invocation parameters only (no permissions field in TOON response).

**Impact:** All 8 plan-marshall agents (and the additional 3 in other bundles, 11 total across the marketplace) are included in OpenCode output with proper permission mapping. They function via OpenCode's `task` tool for subagent dispatch and `skill` tool for skill loading.

**Build failure on unmapped tools:** If an agent uses a tool that has no entry in `frontmatter-rules.json`'s `tool_permissions` map, the target generator logs an error and exits with code 2. Silent exclusion is prohibited — every skipped agent must be a conscious decision. To add support for a new tool, update the JSON config.

### Body Text

Emitted **verbatim except for the mechanical line-level transforms documented in `marketplace/targets/opencode/transforms.md`**. The transforms are bounded — each one is a single-pass regex rewrite over body lines — so the bulk of instructional content is unchanged. The contract is:

- Frontmatter rewritten
- A small fixed set of body transforms applied (see Body Transforms section below)
- Standards/scripts/templates copied verbatim (no transforms)

### Body Transforms

The OpenCode emitter applies two mechanical line-level transforms to skill and command bodies. Both are documented in `marketplace/targets/opencode/transforms.md` and implemented in `body-transforms.py`. Adding a new transform is a deliberate spec change — the emitter does not silently rewrite anything else.

#### Transform 1: `Skill:` directive rewrite

Claude Code's runtime intercepts `Skill: {bundle}:{skill}` directives and loads the named skill into context. OpenCode does not — its `skill` tool is LLM-driven, not runtime-parsed. Without rewriting, the `Skill:` line is just text the LLM may or may not act on.

| Match in source body | Rewrite in OpenCode body |
|----------------------|--------------------------|
| `^Skill:\s+{bundle}:{skill}\s*$` | `Call the \`skill\` tool with \`{ name: "{bundle}-{skill}" }\` before continuing.` |

The regex is anchored to a full line (`^...$`) so inline backtick references like `` `Skill: foo:bar` `` in prose are unaffected. The replacement uses the same `{bundle}-{skill}` namespacing that the emitter produces for skill directories (so the load target always resolves).

#### Transform 2: Slash-command rewrite

Claude Code skills with `user-invocable: true` are invoked as `/skill-name`. On OpenCode the dual-emit places them under `command/{bundle}-{skill}.md`, invoked as `/{bundle}-{skill}` (see User-Invocable Skills below). Cross-references in skill bodies and usage examples must be rewritten to the namespaced form.

**Build-time lookup table:** the emitter walks every source skill with `user-invocable: true` and builds a global `{skill-name → {bundle}-{skill-name}}` map (across all bundles, not per-bundle).

**Body regex:** `(?<![\w-])/(?P<name>{any-known-skill-name})(?=\s|$|=)` → `/{bundle}-{skill-name}`. The lookbehind avoids matching inside paths like `path/to/foo`. The lookahead permits the form `/skill action=...` used in usage examples.

**Argument syntax stays as-is.** Both Claude and OpenCode pass the post-command tail to the LLM as a string; the body's natural-language `key=value` parsing is LLM-driven on both targets, so no further transform is required.

#### What is *not* transformed

The emitter does **not** rewrite:

- Tool-name mentions in prose (`AskUserQuestion`, `EnterPlanMode`, etc.) — these are addressed by source-side cleanup in [03 — Refactor for Portability](03-refactor-for-portability), not at emit time.
- `.claude/` paths or hook event names in prose — same treatment as above.
- Argument syntax (`key=value` vs. `$ARGUMENTS`) — neither runtime parses these; both pass them as a string to the LLM.

Body transforms are reserved for cases where the same source line has different meaning on the two targets (the LLM cannot bridge the gap by itself). Everything else is either source-cleaned or left alone.

### User-Invocable Skills (Dual Emission)

Claude Code skills with `user-invocable: true` in their frontmatter appear as `/skill-name` slash commands in the Claude TUI. OpenCode does **not** support TUI invocation of skills — its `skill` tool is agent-driven only. To preserve user-invocability on OpenCode, every `user-invocable: true` skill is emitted twice:

1. **As a skill** at `target/opencode/skill/{bundle}-{skill}/SKILL.md` — picked up by OpenCode's `skill` tool when an agent decides it's relevant.
2. **As a command wrapper** at `target/opencode/command/{bundle}-{skill}.md` — typed as `/{bundle}-{skill}` in the OpenCode TUI to invoke the skill directly.

**Discovery:** the emitter selects skills for dual emission by reading the source skill's frontmatter `user-invocable: true` field. No `plugin.json` lookup is needed; the frontmatter is the single source of truth.

**Wrapper template** (`marketplace/targets/opencode/templates/user-invocable-command.md`):

```markdown
---
description: {{description}}
{{#model}}model: {{model}}{{/model}}
---

Load and run the `{{skill_id}}` skill via the `skill` tool, then carry out its instructions using the user input below.

User input:

$ARGUMENTS
```

**Substitutions:**

| Placeholder | Source |
|-------------|--------|
| `{{description}}` | Source skill frontmatter `description` |
| `{{model}}` | Source skill frontmatter `model` (mapped via `mapping.json` `model_map`); omitted if unset |
| `{{skill_id}}` | `{bundle}-{skill}` namespaced id (matches the skill directory under `skill/`) |

**Why this template, not the skill body inline:**

- The skill body remains the single source of truth — duplicating it into the command file would invite drift between the two artifacts.
- The wrapper is small (≤10 lines) and fully driven by the source skill's frontmatter, so the emitter generates it mechanically without per-skill exceptions.
- `$ARGUMENTS` is OpenCode's documented argument-substitution token for commands, so user-supplied input is forwarded to the agent that loads the skill.

**Affected count:** 13 plan-marshall + pm-plugin-development skills currently have `user-invocable: true`. The emitter must produce 13 corresponding command wrappers.

**No-op behaviour:** If the source skill has no `description` field, the emitter logs an error and exits with code 2 (same policy as unmapped tools — silent exclusion is prohibited).

## Build Integration

Local developer workflow:

```bash
./pw generate -- --target claude --output target/claude    # Drift check
./pw generate -- --target opencode --output target/opencode  # Emit OpenCode output
./pw generate -- --target all --output target                # Both
```

Add to `pyproject.toml`:
```toml
[tool.pdm.scripts]
generate = "python marketplace/targets/generate.py"
generate-claude = "python marketplace/targets/generate.py --target claude"
generate-opencode = "python marketplace/targets/generate.py --target opencode"
```

## Migration from Existing Adapter

`marketplace/adapters/opencode_adapter.py` contains working logic to port:
- Frontmatter parsing (`parse_frontmatter`)
- Skill/agent/command transforms
- Body transformations — both the existing `Skill:` directive handling and the slash-command rewrite (per `transforms.md`); upgrade the adapter's annotation-only handling into the rewrite specified by Body Transforms above
- Config generation

**Steps:**
1. Port transformation functions into `opencode/frontmatter.py`
2. Port generation logic into `opencode/target.py` as `OpenCodeTarget`
3. Port CLI into `generate.py`
4. Delete `marketplace/adapters/` directory
5. Update any references (search for `marketplace.adapters` imports)

## Gitignore

```gitignore
# Build output directories
target/opencode/
target/claude/
.cursor-plugin/
.codex-plugin/
```

`.claude-plugin/` inside bundles remains **committed** — it is the current source of truth for Claude Code runtime. The Claude target both regenerates it (under `target/claude/`) and verifies that the committed copy matches that regeneration via the equality check.

## Verification

This cluster is complete when:
1. `marketplace/targets/` exists with `TargetBase`, registry, and CLI
2. Claude target equality check passes on committed source AND `--target claude --output target/claude` produces a verbatim mirror plus a freshly-regenerated `plugin.json` per bundle under `target/claude/{bundle}/.claude-plugin/`
3. OpenCode target produces valid output under `target/opencode/` with `skill/`, `agent/`, `command/`, and `opencode.json`
4. Every Claude source skill with `user-invocable: true` produces both a `skill/{bundle}-{skill}/SKILL.md` and a `command/{bundle}-{skill}.md` wrapper
5. `Skill:` directives in OpenCode-emitted bodies are rewritten to `Call the \`skill\` tool …` form per `transforms.md`
6. `/skill-name` slash references in OpenCode-emitted bodies are rewritten to `/{bundle}-{skill-name}` for every `user-invocable: true` skill
7. `./pw generate -- --target {claude,opencode}` works
8. `marketplace/adapters/` retired

## Deploy + Sync Integration

Cluster 02 wires the new target framework into the standard Phase 6
finalize manifest so that every plan in **this meta-project** (the
plan-marshall repo itself) that touches marketplace sources
automatically refreshes the per-target output trees and the host plugin
cache. None of the integration ships to consumer projects — they
install the plan-marshall plugin via Claude Code's standard channel
and never run a generator or push to a cache.

The integration has four moving parts:

1. **`project:finalize-step-deploy-target`** (order 12, project-local
   at `.claude/skills/finalize-step-deploy-target/SKILL.md`) — always
   invokes `python3 marketplace/targets/generate.py --target claude
   --output target/claude` from the plan's worktree. There is no skip
   detector — the generator's per-bundle equality engine handles the
   no-op case (when output equals committed plugin.json, nothing is
   written).

2. **`project:finalize-step-sync-plugin-cache`** (order 14,
   project-local at
   `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md`) —
   invokes the consolidated `sync.py` engine at
   `.claude/skills/sync-plugin-cache/scripts/sync.py`, which reads
   `target/claude/`, runs the staleness guard, fans out parallel rsync
   calls per bundle, and aggregates the results. Order 14 places it
   immediately after `project:finalize-step-deploy-target` (12) and
   before `default:create-pr` (20), so the cache is fresh before any
   agent-dispatched step runs.

3. **Project-local `sync-plugin-cache` skill** at
   `.claude/skills/sync-plugin-cache/`. The consolidated `sync.py`
   engine serves both the user-invocable workflow
   (`/sync-plugin-cache`) and the project-local finalize step. The
   `list_bundles_and_versions.py` helper sits alongside it; both
   default `--source-root` to `target/claude/` so the canonical source
   is the multi-target generator output rather than the raw bundles
   tree. Why project-local: the engine only makes sense in repos that
   own marketplace bundle sources, which is just this one. Consumer
   projects of plan-marshall do not need (and would be confused by) a
   `/sync-plugin-cache` slash command.

4. **Always-generate plugin.json with equality gate** — the Claude
   target's per-bundle `plugin_json_gen.py` always produces the
   complete, sorted plugin.json from on-disk components, then the
   `equality_check.py` engine compares it against the committed
   `marketplace/bundles/{bundle}/.claude-plugin/plugin.json`. When they
   match, the per-bundle write is short-circuited. The always-generate
   design supersedes the previous drift-detection narrative; the
   equality gate is what makes "always run" free.

**`bundle_self_modification` rule removal.** The previous design relied
on a stacked rule in `manage-execution-manifest` that detected bundle
source modifications and inserted an early
`project:finalize-step-sync-plugin-cache` step before the first
agent-dispatched step. Cluster 02 retires that rule entirely — the
project-local marshal.json ordering already places
`project:finalize-step-sync-plugin-cache` unconditionally before agent
dispatches, so the same outcome is achieved structurally rather than
by a mutation. See the historical lesson `2026-04-26-23-003` for the
rule's original motivation.

## Dependencies

- `01-design-platform-api` — target engine needs to know the API surface to generate valid platform instructions
- Can start in parallel with 01, but final integration requires 01 complete
