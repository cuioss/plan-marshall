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
│   ├── mapping.json         # Tool + model + layout mappings
│   └── frontmatter-rules.json  # Frontmatter transform rules
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

## Claude Target (Drift Detection)

**Behavior:** Validation only. The source of truth is already Claude Code format in `marketplace/bundles/`. This target:
1. Reads each bundle's `plugin.json` and `.claude-plugin/`
2. Compares committed manifests to what it would generate from source
3. Reports drift as TOON and exits with code 2 if any mismatch found

**Why drift matters:** If someone edits a skill but forgets to update `plugin.json` (orphan reference), the Claude target catches it.

**Output:** Drift report as TOON. Exit 0 if no drift, exit 2 if drift detected.

**Not a deployment target:** The Claude target does NOT produce deployable artifacts — it only validates that the committed Claude Code format is internally consistent. Claude Code consumes `marketplace/bundles/` directly from the GitHub repo (see [05 — Distribution](05-distribution)).

## OpenCode Target (Format Emitter)

**Behavior:** Full emitter. Translates Claude Code source format into OpenCode's expected structure inside the output directory (default: `target/opencode/`):

```
target/opencode/
├── skills/
│   └── {bundle}-{skill}/
│       └── SKILL.md
├── agents/
│   └── {agent}.md
├── commands/
│   └── {command}.md
└── opencode.json
```

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
    "opus": "claude-opus-4-5",
    "sonnet": "claude-sonnet-4-5",
    "haiku": "claude-haiku-4-5"
  },
  "required_fields": ["description"],
  "optional_fields": ["model", "mode"]
}
```

**Note:** The generator adds the `anthropic/` provider prefix when writing `opencode.json`, so model IDs here are without prefix.

#### Configuration: `marketplace/targets/opencode/frontmatter-rules.json`

Uses `tool_permissions` and `model_map` from `mapping.json` (loaded by the frontmatter engine at runtime).

```json
{
  "required_fields": ["description"],
  "optional_fields": ["model", "mode"]
}
```

### Model Mapping Rationale

Claude Code aliases (`opus`, `sonnet`, `haiku`) resolve to the latest version. OpenCode requires explicit model IDs. The generator maps to the current available version to preserve the skill author's intent:

- `opus` → `claude-opus-4-5` (deep reasoning, reliable rule following; avoids `claude-opus-4-7` which may not be available in OpenCode's built-in provider)
- `sonnet` → `claude-sonnet-4-5` (daily coding)
- `haiku` → `claude-haiku-4-5` (simple tasks)

**Note:** OpenCode provider prefix (`anthropic/`) is added by the config generator, not included in the model ID mapping.

**No forced downgrades.** If a skill specifies `opus`, the OpenCode output preserves that requirement.

### Limitation: Instruction Following

Research shows OpenCode's instruction injection mechanism differs from Claude Code's:

- **Claude Code:** `CLAUDE.md` is injected as a "system reminder" that persists through compaction and is re-injected into context throughout the session
- **OpenCode:** `AGENTS.md` is loaded once at session start. As context compacts, instructions may be lost
- **Known issue (#8892):** Anthropic models in OpenCode sometimes ignore `instructions` array content entirely
- **Known issue (#11441):** OpenCode's Plan agent does not enforce plan rules architecturally — it relies on the LLM to respect them voluntarily

**Temperature does not solve this.** OpenCode supports `temperature: 0.1` for more deterministic output, but this affects creativity, not instruction comprehension. A model that cannot understand complex rules at `temperature=0.7` will not suddenly understand them at `temperature=0.1`.

**Practical implication:** For skills with complex multi-step workflows (like plan-marshall's 55 skills), `opus` is strongly recommended. Mapping `opus` to `sonnet` to save costs will degrade reliability.

### Agent Mapping

Agents with `Task` or `Skill` in their `tools:` frontmatter are **not** Claude-only. OpenCode has equivalent `task` and `skill` tools. See [01 — Design Platform API](01-design-platform-api) for the full tool mapping table.

**Implementation note:** Permissions are set in agent frontmatter or `opencode.json`, not at `task` invocation time. The `subagent dispatch` operation returns invocation parameters only (no permissions field in TOON response).

**Impact:** All 10 plan-marshall agents are included in OpenCode output with proper permission mapping. They function via OpenCode's `task` tool for subagent dispatch and `skill` tool for skill loading.

**Build failure on unmapped tools:** If an agent uses a tool that has no entry in `frontmatter-rules.json`'s `tool_permissions` map, the target generator logs an error and exits with code 2. Silent exclusion is prohibited — every skipped agent must be a conscious decision. To add support for a new tool, update the JSON config.

### Body Text

Emitted **verbatim**. No transformation of instructional content. Only:
- Frontmatter rewritten
- Comment annotations added for `Skill:` directives
- Standards/scripts/templates copied verbatim

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
- Body `Skill:` directive annotation
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

`.claude-plugin/` inside bundles remains **committed** — it is the current source of truth for Claude Code runtime. The Claude target validates it; it does not regenerate it.

## Verification

This cluster is complete when:
1. `marketplace/targets/` exists with `TargetBase`, registry, and CLI
2. Claude target produces zero drift on committed source
3. OpenCode target produces valid output under `target/opencode/` with `skills/`, `agents/`, `commands/`, and `opencode.json`
4. `./pw generate -- --target {claude,opencode}` works
5. `marketplace/adapters/` retired

## Dependencies

- `01-design-platform-api` — target engine needs to know the API surface to generate valid platform instructions
- Can start in parallel with 01, but final integration requires 01 complete
