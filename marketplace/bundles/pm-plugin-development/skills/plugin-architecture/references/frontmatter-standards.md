# Frontmatter Standards

YAML frontmatter configuration standards for agents, commands, and skills in the marketplace.

## Table of Contents

1. [Frontmatter Format](#frontmatter-format)
2. [Agent Frontmatter](#agent-frontmatter)
3. [Command Frontmatter](#command-frontmatter)
4. [Skill Frontmatter](#skill-frontmatter)
5. [Target Scoping](#target-scoping)
6. [Tools Declaration](#tools-declaration)
7. [Common Issues](#common-issues)
8. [Validation Rules](#validation-rules)

## Frontmatter Format

### Basic Structure

All markdown files (agents, commands, skills) use YAML frontmatter at the top:

```markdown
---
name: component-name
description: Clear description of what this does
tools: Read, Write, Edit, Bash
---

# Component content starts here
```

### Critical Rules

1. **Frontmatter delimiters**: Must be exactly `---` (three hyphens) on separate lines
2. **No blank lines**: Between opening `---` and first field, or between fields and closing `---`
3. **Field syntax**: `field-name: value` with single space after colon
4. **Tools format**: **Comma-separated**, NOT array syntax

## Agent Frontmatter

### Required Fields

```yaml
---
name: agent-name
description: |
  Multi-line description of what agent does.

  Examples:
  - Input: parameter=value
  - Output: What agent returns
tools: Read, Write, Edit, Bash, Grep, Glob
---
```

#### Field Specifications

**name** (required):
- Pattern: `^[a-z0-9-]+$` (lowercase letters, numbers, hyphens only)
- Max length: 64 characters
- Must be unique across all agents in marketplace
- Examples: `diagnose-skill`, `java-fix-javadoc`

**description** (required):
- Min length: 50 characters (recommended)
- Max length: 1024 characters
- Should include:
  - What the agent does (1-2 sentences)
  - Input parameters expected
  - Output format returned
- Multi-line format using `|` is recommended for readability

**tools** (required):
- Format: **Comma-separated list** (NOT array syntax)
- Available tools: `Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `Task`
- **CRITICAL**: Do NOT include `Task` tool (see Pattern 18 in architecture-rules.md)
- Bash permissions can include wildcards: `Bash(git:*)`, `Bash(./script.sh:*)`
- See [Tools Declaration](#tools-declaration) for detailed rules

### Optional Fields

```yaml
model: sonnet
color: blue
```

**model** (optional):
- Valid values: `sonnet`, `opus`, `haiku`
- Default: Inherits from parent/thread
- Recommendation: Use `haiku` for simple, deterministic tasks to reduce cost

**color** (optional):
- Valid values: `red`, `orange`, `yellow`, `green`, `blue`, `purple`, `pink`, `gray`
- Purpose: Visual identification in UI
- No functional impact

**targets** (optional):
- Build-time field naming the build targets this agent ships to; absent means every target
- See [Target Scoping](#target-scoping) for the format, the validation rules, and the admission test

### Complete Agent Example

```yaml
---
name: diagnose-skill
description: |
  Analyzes comprehensive quality of a single skill: validates structure, YAML, and standards quality.

  Examples:
  - Input: skill_path=/path/to/skill
  - Output: Comprehensive skill quality report with issues categorized by severity

tools: Read, Glob, Bash(./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)
model: sonnet
color: orange
---
```

## Command Frontmatter

### Required Fields

```yaml
---
name: command-name
description: Brief description of command purpose
tools: Read, Bash
---
```

#### Field Specifications

Commands use the same field specifications as agents with these differences:

**name** (required):
- Same rules as agents
- Will be invoked as `/command-name` by users
- Examples: `java-fix-javadoc`, `plugin-doctor`

**description** (required):
- Can be briefer than agents (30+ characters acceptable)
- Should be single-line for commands
- Focus on user-facing purpose, not technical details

**tools** (required):
- Commands can use `Task` tool to invoke agents (Pattern 6: Commands Orchestrate, Agents Execute)
- Same comma-separated format as agents

### Optional Fields

Same as agents: `model`, `color`, `targets` (see [Target Scoping](#target-scoping))

### Complete Command Example

```yaml
---
name: java-fix-javadoc
description: Fix Javadoc errors and warnings from Maven builds with content preservation
tools: Read, Edit, Write, Bash, Grep, Task
model: sonnet
color: green
---
```

## Skill Frontmatter

### Required Fields

```yaml
---
name: skill-name
description: Brief description of skill domain
user-invocable: true
---
```

#### Field Specifications

**name** (required):
- Same pattern as agents/commands: `^[a-z0-9-]+$`
- Max length: 64 characters
- Examples: `cui-java-core`, `cui-marketplace-architecture`

**description** (required):
- Min length: 30 characters
- Max length: 500 characters
- Should describe the standards domain covered
- Single-line preferred

**user-invocable** (required):
- **Field name**: `user-invocable`
- **Values**: `true` or `false`
- `true`: Skill appears in slash menu and can be invoked directly by users (e.g., `/plugin-doctor`)
- `false`: Internal skill, not directly user-invocable (e.g., reference libraries, internal utilities)
- **CRITICAL**: Every skill MUST have this field explicitly set
- See [User-Invokable Guidelines](#user-invocable-guidelines) for when to use each value

### Optional Fields

Skills do not use `model`, `color`, or `tools`/`allowed-tools` fields. The plugin schema for skills supports only: `name`, `description`, `user-invocable`, `mode`, `argument-hint`, `compatibility`, `disable-model-invocation`, `license`, `metadata`, `profiles`, `priming_preamble`, `composes`.

That list is the **runtime** schema — the fields the host platform reads from an installed skill. `targets` (see [Target Scoping](#target-scoping)) is not in it and does not need to be: it is a build-time field the multi-target generator consumes from the source bundle when deciding whether to emit the skill at all. It is therefore a top-level field rather than a `metadata:` sub-key — `metadata:` is the escape hatch for keys that must be *recognized at runtime*, which this one never is.

**implements** (optional):

Declares that this skill implements an extension point contract.

- **Format**: `bundle:skill/path` — references the contract document relative to the skill's root
- **Example**: `implements: plan-marshall:extension-api/standards/ext-point-triage`
- **Validation**: plugin-doctor verifies the referenced contract exists and the skill satisfies its required sections
- **Used by**: Marketplace inventory dependency tracking (`_dep_detection.py::detect_implements()`), plugin-doctor contract validation
- **When to use**: Any skill that implements an extension point (triage, outline, recipe, build). For credential extensions (Python files, not SKILL.md), use a docstring reference instead.

```yaml
---
name: ext-triage-java
description: Java finding triage with suppression syntax and severity guidelines
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-triage
---
```

**mode** (required):

Declares the skill's execution archetype — the single, authoritative signal for how the skill is consumed. `mode` is the **sole source of truth** for the archetype; it replaces the prose `**REFERENCE MODE**` line and the Enforcement-block `**Execution mode**:` line that skills previously carried.

- **Field name**: `mode`
- **Values** (closed enum — exactly one of):

  | Value | Meaning |
  |-------|---------|
  | `knowledge` | Load for context only — reference libraries, standards documents, and the knowledge content of manifests. Its body is reference material, **never executed as instructions**. |
  | `workflow` | The LLM follows the skill's documented workflow steps sequentially (multi-step procedures, wizards, phase skills, fetch-triage-implement loops, dumb task runners). |
  | `script-executor` | The skill drives documented executor scripts and routes on their TOON status with minimal LLM reasoning (subcommand-routing skills, `script-deterministic` analyzer/library suites — no LLM judgement). |
  | `manifest` | An extension manifest — a read-only contract surface modified **only via the Extension API contract**, never edited as a free-form document. |

- **Placement**: in the YAML frontmatter, after the `user-invocable:` line.
- **Validation**: the plugin-doctor `skill-missing-mode` rule flags any skill whose frontmatter omits `mode` or carries a value outside the enum above.
- **Compliance**: agents reading a loaded skill comply with its declared `mode` — see the "Skill mode: comply with the declared archetype" rule in `plan-marshall:persona-plan-marshall-agent` (`standards/agent-behavior-rules.md`).

```yaml
---
name: java-core
description: Core Java development standards for patterns, modern features, and performance optimization
user-invocable: false
mode: knowledge
---
```

**profiles** (optional):

Declares the closed list of persona identifiers — work-activity profiles — that a `persona-*` skill is applicable for. It is the binding source of truth the persona resolver (`manage-personas resolve`) reads to flatten a persona's composition DAG into a deduped `skills[]`.

- **Field name**: `profiles`
- **Format**: a YAML list of profile identifiers (multi-capable). The **first entry is the primary identity profile** — the one a persona is reverse-looked-up by from a task's profile. Later entries are secondary profiles the persona also applies (e.g. a work persona that also applies the `quality` ref).
- **Scope**: only on `persona-*` skills. A persona that has no work-activity profile (a meta/evaluator persona that composes other personas as lenses) omits the field entirely; a `ref-*` skill never carries it.
- **Uniqueness**: no two work personas may share the same primary (first) profile — enforced by the plugin-doctor `persona-profile-uniqueness` rule.

```yaml
---
name: persona-implementer
description: Production-code implementation persona
user-invocable: false
mode: knowledge
implements: persona
profiles: [implementation, quality]
---
```

**priming_preamble** (optional):

An optional persona-scoped loading preamble override — data only. The field is read by persona tooling but emits no target render in this plan (it is reserved for a later per-target render concept).

- **Field name**: `priming_preamble`
- **Format**: a YAML scalar (a string). Omit the field when no override is needed.
- **Scope**: only on `persona-*` skills.

```yaml
---
name: persona-code-reviewer
description: Code-review persona that composes other personas as evaluation lenses
user-invocable: false
mode: knowledge
implements: persona
priming_preamble: "Adopt a reviewer's stance: read for correctness and intent, not authorship."
---
```

**composes** (optional):

Declares the **machine-readable composition edges** of a `persona-*` skill — the `bundle:skill` notations (`ref-*` concerns and, for meta/evaluator personas, other `persona-*` skills) that the persona DIRECTLY composes. It is the data source the persona resolver (`manage-personas resolve`) reads to walk the composition DAG; the prose `## Composition` section remains as human-facing documentation, but `composes:` is the resolver's binding source of truth — no nested skill loading and no hardcoded composition table.

- **Field name**: `composes`
- **Format**: a YAML list of `bundle:skill` notations. Each entry names a `ref-*` skill the persona applies or a `persona-*` skill the persona composes as a lens. The base `persona-plan-marshall-agent` is NOT listed — the resolver always includes the base unconditionally.
- **Scope**: only on `persona-*` skills. Omit the field entirely when a persona composes nothing directly (it resolves via its `profiles:` alone, or it is the base). A `ref-*` skill never carries it.
- **DAG**: composition edges must form a directed acyclic graph (base is a leaf composed by all; meta personas compose work personas; no cycles). The resolver detects and rejects cycles.

```yaml
---
name: persona-implementer
description: Production-code implementation persona
user-invocable: false
mode: knowledge
implements: persona
profiles: [implementation, quality]
composes: [plan-marshall:ref-code-quality]
---
```

A meta/evaluator persona lists the work personas it uses as evaluation lenses:

```yaml
---
name: persona-code-reviewer
description: Code-review persona that composes other personas as evaluation lenses
user-invocable: false
mode: knowledge
implements: persona
composes: [plan-marshall:persona-implementer, plan-marshall:persona-module-tester]
---
```

**metadata** (optional):

A nested mapping that is the supported **escape hatch** for declaring well-known keys the closed top-level skill schema does not define. Because the top-level skill frontmatter schema is closed (see the supported-field list above), a bare top-level key the schema does not name is silently ignored — keys that are not first-class top-level fields are carried under `metadata:` instead, where they are recognized.

- **Field name**: `metadata`
- **Format**: a YAML mapping of recognized sub-keys.
- **Recognized sub-keys**:

  | Sub-key | Type | Meaning |
  |---------|------|---------|
  | `verification_profile` | str | The producer's [`ext-point-verify`](../../../../plan-marshall/skills/extension-api/standards/ext-point-verify.md) declaration. A producer SKILL.md opts into the findings-pipeline verify stage by declaring this key; its value is a verify-profile key (e.g. `security`) that resolves to the verify skill applied to that producer's findings before triage. Absent → the producer does not participate in the verify stage. The canonical field definition and the implementor-record contract live in `ext-point-verify.md` — this entry only registers the key as recognized so plugin-doctor does not flag it as unknown. |

```yaml
---
name: recipe-security-audit
description: On-demand security-audit recipe that emits findings into the triage pipeline
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
metadata:
  verification_profile: security
---
```

### User-Invocable Guidelines

**Use `user-invocable: true` when**:
- Skill provides a user-facing workflow (e.g., `/plugin-doctor`, `/plan-retrospective`)
- Skill should appear in slash menu for direct invocation
- Skill is the primary entry point for a capability

**Use `user-invocable: false` when**:
- Skill is a reference library (Pattern 10) - pure documentation
- Skill is an internal utility invoked only by other skills/agents
- Skill is an extension point (e.g., `ext-triage-java`)
- Skill is a plugin manifest (e.g., `plan-marshall-plugin`)

### plugin.json Registration Convention

**Not all skills need plugin.json registration.** Registration controls whether the host platform loads the skill's SKILL.md as LLM context. Skills accessed only via the script executor (`python3 .plan/execute-script.py bundle:skill:script`) don't need their SKILL.md loaded — the executor resolves scripts by filesystem path.

**Three categories of skills:**

| Category | plugin.json | Example |
|----------|-------------|---------|
| **User-invocable** (`user-invocable: true`) | Required | `plugin-doctor`, `phase-3-outline` |
| **Context-loaded** (`user-invocable: false`, loaded via `Skill:` directive) | Required | `manage-tasks`, `manage-lessons` |
| **Script-only** (`user-invocable: false`, accessed only via script notation) | Not needed | `manage-files`, `manage-logging` |

**How to determine the category:**
1. If `user-invocable: true` → register in plugin.json
2. If any component uses `Skill: bundle:skill-name` to load it as LLM context → register in plugin.json
3. If all references are 3-part script notations (`bundle:skill:script` with `execute-script.py`) → do NOT register

**Script-only skills are still installed.** Bundle installation copies the entire directory tree via rsync. Script-only skills are physically present and discoverable by the executor generator — they just aren't loaded into LLM context (which saves tokens).

**Naming convention:** Script-only skills typically follow the `manage-*` or `tools-*` prefix pattern, signaling they are programmatic APIs rather than knowledge to be loaded.

### Complete Skill Examples

**User-Invokable Skill** (appears in slash menu):
```yaml
---
name: plugin-doctor
description: Diagnose and fix quality issues in marketplace components
user-invocable: true
mode: script-executor
---
```

**Context-Loaded Internal Skill** (loaded by other skills/agents via `Skill:` directive):
```yaml
---
name: manage-tasks
description: Task CRUD operations for planning workflow
user-invocable: false
mode: script-executor
---
```

**Script-Only Skill** (accessed only via executor, no plugin.json entry):
```yaml
---
name: manage-files
description: File operations for plan work directories
user-invocable: false
mode: script-executor
---
```

## Target Scoping

### `targets` (optional — agents, commands, and skills alike)

Declares the closed list of build targets a component ships to. It is a **build-time** field: the multi-target generator reads it from the source bundle and decides whether to emit the component at all.

```yaml
---
name: tools-fix-intellij-diagnostics
description: Retrieve and fix IDE diagnostics automatically
tools: Read, Edit, Task, mcp__ide__getDiagnostics
targets: [claude]
---
```

**Semantics**:

- **Field absent ⇒ every target.** This is the default and the overwhelmingly common case. Omitting the field is how an author says "ship everywhere"; nearly every component in the marketplace omits it.
- **Field present ⇒ only the targets named.** On every other target the component is simply **absent** — no stub, no runtime no-op, no empty file.
- **Format**: a YAML list, inline (`targets: [claude]`) or block form. Values are build-target registry names — derive the live set from `TARGET_REGISTRY` in `marketplace/targets/__init__.py`; it is the source of truth and is never enumerated in prose.
- **Scope of one declaration**: an agent's or a command's declaration governs that one file. A skill's declaration lives on its `SKILL.md` and governs the **whole skill directory**, its `standards/`, `references/`, `templates/`, and `scripts/` sub-trees included. Files *inside* a skill are not individually scopable.

**Validation** — every one of these **fails the build**, because a component silently shipping to fewer targets than intended is exactly the defect the field exists to prevent:

| Declaration | Outcome |
|---|---|
| A name absent from `TARGET_REGISTRY` (a typo) | Build fails, naming the component and the unknown value |
| `targets: []` | Build fails — a component shipped nowhere is an authoring error, not an intent |
| Only targets that emit no component tree | Build fails — such a declaration also ships the component nowhere |

The plugin-doctor `targets-scope-invalid` rule reports the first two at authoring time so the defect surfaces before the build. The third needs each target's `emits_bundle_tree` capability and is checked by the build alone.

### Admission test — when a target-scoped component is the right answer

A target-scoped component is the **fourth** placement home, and it is gated. A capability that exists everywhere but *behaves* differently belongs behind a runtime operation (uniform contract, per-target implementation); emitted-text and emitted-frontmatter vocabulary belongs in the build target's `mapping.json` data. Reach for `targets:` only when all three of these hold:

1. It is a whole workflow or knowledge body — not reducible to a single runtime operation or to a body/frontmatter transform.
2. It is genuinely not applicable on other targets, rather than merely hard to abstract.
3. Normalizing it would force a no-op operation onto every other target, or distort the shared contract.

It must never be used to dodge normalization: format-coupling (metrics shape, permission DSL, tool-name vocabulary) still normalizes into the runtime and build-target homes. The field is for target-bound *capabilities*, never for the per-target *rendering* of a shared one.

**Cross-references are the author's responsibility.** Scoping a component away from a target does not rewrite references to it from components that still ship there. A component that scopes itself out of a target should not be the only path to a capability the remaining components point at.

## Tools Declaration

### Correct Format: Comma-Separated

**CRITICAL**: Official Claude Code documentation specifies **comma-separated format**.

PASS **CORRECT**:
```yaml
tools: Read, Write, Edit, Bash, Grep, Glob
```

FAIL **INCORRECT** (array syntax):
```yaml
tools: [Read, Write, Edit, Bash, Grep, Glob]
```

FAIL **INCORRECT** (newlines):
```yaml
tools:
  - Read
  - Write
  - Edit
```

### Bash Tool with Wildcards

When using Bash with specific permissions:

PASS **CORRECT**:
```yaml
tools: Read, Bash(git:*), Bash(npm:*)
```

PASS **CORRECT** (script paths):
```yaml
tools: Read, Glob, Bash(./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)
```

FAIL **INCORRECT** (array syntax even for Bash):
```yaml
tools: [Read, Bash(git:*)]
```

### Tool Ordering

**Recommendation**: Declare tools in order of usage frequency:
1. Common tools first: `Read`, `Write`, `Edit`
2. Utility tools: `Grep`, `Glob`
3. Execution tools: `Bash`, `Task`

**Example**:
```yaml
tools: Read, Edit, Write, Grep, Glob, Bash
```

This improves readability but has no functional impact.

## Common Issues

### Issue 1: Grep Breaking Bash Tool Parsing

An undocumented edge case in Claude Code's frontmatter parser: listing `Grep` alongside a parameterized `Bash(...)` entry causes the Bash permission to fail ("Bash tool not available"). **Fix**: remove `Grep` from the frontmatter tools declaration — workflow steps can still use Grep without declaring it. Correct: `tools: Read, Glob, Bash(./.claude/skills/script.sh:*)`.

### Issue 2: Array Syntax vs Comma-Separated

Use the documented comma-separated form (`tools: Read, Write, Edit, Bash, Grep, Glob`) rather than YAML array form (`tools: [Read, Write, Edit, Bash, Grep, Glob]`).

### Issue 3: Task Tool in Agents

Agents must not declare `Task` — the host platform restricts Task from sub-agents and the agent will error at runtime. If orchestration is needed, create a command (commands may declare `Task` and invoke agents via `Task: subagent_type: {bundle}:{agent}`).

### Issue 4: Unsupported Fields in Skills

Skills must not declare `allowed-tools` or `tools`. The runtime skill schema only supports: `name`, `description`, `user-invocable`, `mode`, `argument-hint`, `compatibility`, `disable-model-invocation`, `license`, `metadata`, `profiles`, `priming_preamble`, `composes`. Any other field is silently ignored at runtime — remove it, unless it is a build-time field the generator consumes before the artifact exists (`targets`, see [Target Scoping](#target-scoping)).

### Issue 5: Invalid Tool Names

Tool names are case-sensitive. Use exactly: `Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `Task` (commands only), `Skill` (commands/agents only). Lowercase, uppercase, and invented names (`File`, `Search`) are invalid.

## Validation Rules

### YAML Validation

1. **Syntax**: Must be valid YAML
2. **Required fields**: Must be present and non-empty
3. **Field names**: Must match exactly (case-sensitive)
4. **Delimiters**: Exactly `---` on separate lines

**Detection Script**: `analyze-markdown-file.sh` validates YAML frontmatter

### Tools Validation

1. **Format**: Must be comma-separated (not array, not newline-separated)
2. **Tool names**: Must be from valid tool list
3. **Capitalization**: Must match exactly (`Read` not `read`)
4. **Task tool**: Must not be in agents (commands only)
5. **Grep tool**: Should not be combined with parameterized Bash
6. **Field name**: `tools` for agents/commands only (skills do not have tool declarations)

**Detection Script**: `analyze-markdown-file.sh` and `analyze-skill-structure.sh` validate tools

### Permission Patterns

#### Skill Script Mounting

**CRITICAL CONCEPT**: Skills are mounted at runtime from their physical location to `./.claude/skills/`.

**Physical Location**:
```text
marketplace/bundles/pm-plugin-development/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh
```

**Runtime Mount Point**:
```text
./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh
```

**Why This Matters**:
1. Agents/commands use **runtime paths** in frontmatter (`./.claude/skills/...`)
2. The host platform mounts skills when loaded
3. This is NOT a relative path to "fix" - it's the correct runtime mount point
4. Do NOT use physical marketplace paths in frontmatter

#### Bash Tool Script Permissions

When using Bash tool to execute scripts located in skills:

PASS **CORRECT frontmatter declaration**:
```yaml
tools: Read, Glob, Bash(./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)
```

FAIL **INCORRECT** (physical path):
```yaml
tools: Read, Bash(./marketplace/bundles/pm-plugin-development/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)
```

FAIL **INCORRECT** (absolute path):
```yaml
tools: Read, Bash(/Users/oliver/git/plan-marshall/marketplace/bundles/.../scripts/analyze-skill-structure.sh:*)
```

#### Settings.json Permission Requirements

**CRITICAL**: Permissions must be declared in **both** global and project-level settings.

**Why Both Are Required**:
- Global settings (`~/.claude/settings.json`): Base permissions
- Project settings (`.claude/settings.json`): Can restrict or augment global permissions
- If script permission missing from either, agents cannot execute scripts

**Global Settings** (`~/.claude/settings.json`):
```json
{
  "permissions": {
    "allow": [
      "Bash(./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)",
      "Bash(./marketplace/bundles/pm-plugin-development/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)",
      "Bash(/Users/username/git/project/marketplace/bundles/.../scripts/analyze-skill-structure.sh:*)"
    ]
  }
}
```

**Project Settings** (`.claude/settings.json`):
```json
{
  "permissions": {
    "allow": [
      "Bash(./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)",
      "Bash(./marketplace/bundles/pm-plugin-development/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)",
      "Bash(/Users/username/git/project/marketplace/bundles/.../scripts/analyze-skill-structure.sh:*)"
    ]
  }
}
```

**Why Multiple Path Formats**:
1. `./.claude/skills/...` - Runtime mount point (used by agents at runtime)
2. `./marketplace/bundles/...` - Relative physical path (main conversation)
3. `/Users/.../marketplace/bundles/...` - Absolute physical path (validation/testing)

All three formats are needed to ensure scripts work in all contexts.

#### Command Wildcards

For general bash commands (not scripts):

PASS **CORRECT**:
```yaml
tools: Bash(git:*), Bash(npm:*), Bash(mvn:*)
```

**Wildcard Behavior**:
- `:*` suffix enables prefix matching
- `git:*` permits all git subcommands: `git status`, `git commit`, etc.
- `npm:*` permits all npm commands: `npm install`, `npm run test`, etc.

#### Security Notes

1. **Convenience, Not Security**: Bash permission patterns are prefix matches, not enforced security boundaries
2. **Can Be Bypassed**: Users can work around these restrictions
3. **Purpose**: Convenience layer to prevent accidental operations, not foolproof isolation

## Quality Rules

Use this checklist when creating or reviewing frontmatter:

**All Components** (agents, commands, skills):
- YAML frontmatter present with `---` delimiters
- `name` field present with valid pattern `^[a-z0-9-]+$`
- `description` field present with adequate length
- No blank lines in frontmatter
- Valid YAML syntax (no tabs, proper spacing)
- `targets` field, if present, is non-empty and names only registered build targets — and the component meets the three-condition admission test in [Target Scoping](#target-scoping)

**Agents**:
- `tools` field uses comma-separated format (not array)
- Tools list does NOT include `Task`
- Tools list does NOT include `Grep` if using parameterized `Bash`
- `description` includes input/output examples
- `model` field (if present) uses valid value: `sonnet`, `opus`, `haiku`
- `color` field (if present) uses valid color name

**Commands**:
- `tools` field uses comma-separated format (not array)
- Can include `Task` tool if orchestrating agents
- Tools list does NOT include `Grep` if using parameterized `Bash`
- `description` is user-focused (what command does, not how)

**Skills**:
- No `tools`, `allowed-tools`, `model`, or `color` fields (not supported for skills)
- **`user-invocable` field present** (either `true` or `false`)
- `user-invocable` value matches skill purpose (true for user-facing, false for internal)
- **`mode` field present** with a value from the closed enum `{knowledge, workflow, script-executor, manifest}`
- `mode` value matches the skill's archetype (knowledge for reference/standards, workflow for step procedures, script-executor for executor-driven analyzers/libraries, manifest for extension manifests)

## Reference

**Related Standards**:
- agent-quality-standards.md - Comprehensive agent quality requirements
- command-quality-standards.md - Comprehensive command quality requirements
- architecture-rules.md - Pattern 18 (Task tool restrictions), Pattern 6 (Orchestration)
- script-development.md - Bash script integration patterns

**Official Documentation**:
- Claude Code documentation: https://docs.claude.com/en/docs/claude-code/settings
- Agent SDK: https://platform.claude.com/docs/en/agent-sdk/subagents
