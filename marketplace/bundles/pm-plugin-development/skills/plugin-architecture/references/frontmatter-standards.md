# Frontmatter Standards

YAML frontmatter configuration standards for agents, commands, and skills in the marketplace.

## Table of Contents

1. [Frontmatter Format](#frontmatter-format)
2. [Agent Frontmatter](#agent-frontmatter)
3. [Command Frontmatter](#command-frontmatter)
4. [Skill Frontmatter](#skill-frontmatter)
5. [Tools Declaration](#tools-declaration)
6. [Common Issues](#common-issues)
7. [Validation Rules](#validation-rules)

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
- Examples: `java-fix-javadoc`, `plugin-diagnose-skills`

**description** (required):
- Can be briefer than agents (30+ characters acceptable)
- Should be single-line for commands
- Focus on user-facing purpose, not technical details

**tools** (required):
- Commands can use `Task` tool to invoke agents (Pattern 6: Commands Orchestrate, Agents Execute)
- Same comma-separated format as agents

### Optional Fields

Same as agents: `model`, `color`

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
user-invokable: true
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

**user-invokable** (required):
- **Field name**: `user-invokable` (note the 'k' spelling)
- **Values**: `true` or `false`
- `true`: Skill appears in slash menu and can be invoked directly by users (e.g., `/plugin-doctor`)
- `false`: Internal skill, not directly user-invokable (e.g., reference libraries, internal utilities)
- **CRITICAL**: Every skill MUST have this field explicitly set
- See [User-Invokable Guidelines](#user-invokable-guidelines) for when to use each value

### Optional Fields

Skills do not use `model`, `color`, or `tools`/`allowed-tools` fields. The plugin schema for skills supports only: `name`, `description`, `user-invokable`, `argument-hint`, `compatibility`, `disable-model-invocation`, `license`, `metadata`.

### User-Invokable Guidelines

**Use `user-invokable: true` when**:
- Skill provides a user-facing workflow (e.g., `/plugin-doctor`, `/verify-workflow`)
- Skill should appear in slash menu for direct invocation
- Skill is the primary entry point for a capability

**Use `user-invokable: false` when**:
- Skill is a reference library (Pattern 10) - pure documentation
- Skill is an internal utility invoked only by other skills/agents
- Skill is an extension point (e.g., `ext-triage-java`)
- Skill is a plugin manifest (e.g., `plan-marshall-plugin`)

### plugin.json Registration Convention

**Not all skills need plugin.json registration.** Registration controls whether Claude Code loads the skill's SKILL.md as LLM context. Skills accessed only via the script executor (`python3 .plan/execute-script.py bundle:skill:script`) don't need their SKILL.md loaded — the executor resolves scripts by filesystem path.

**Three categories of skills:**

| Category | plugin.json | Example |
|----------|-------------|---------|
| **User-invocable** (`user-invokable: true`) | Required | `plugin-doctor`, `phase-3-outline` |
| **Context-loaded** (`user-invokable: false`, loaded via `Skill:` directive) | Required | `manage-tasks`, `manage-lessons` |
| **Script-only** (`user-invokable: false`, accessed only via script notation) | Not needed | `manage-files`, `manage-logging` |

**How to determine the category:**
1. If `user-invokable: true` → register in plugin.json
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
user-invokable: true
---
```

**Context-Loaded Internal Skill** (loaded by other skills/agents via `Skill:` directive):
```yaml
---
name: manage-tasks
description: Task CRUD operations for planning workflow
user-invokable: false
---
```

**Script-Only Skill** (accessed only via executor, no plugin.json entry):
```yaml
---
name: manage-files
description: File operations for plan work directories
user-invokable: false
---
```

## Tools Declaration

### Correct Format: Comma-Separated

**CRITICAL**: Official Claude Code documentation specifies **comma-separated format**.

✅ **CORRECT**:
```yaml
tools: Read, Write, Edit, Bash, Grep, Glob
```

❌ **INCORRECT** (array syntax):
```yaml
tools: [Read, Write, Edit, Bash, Grep, Glob]
```

❌ **INCORRECT** (newlines):
```yaml
tools:
  - Read
  - Write
  - Edit
```

### Bash Tool with Wildcards

When using Bash with specific permissions:

✅ **CORRECT**:
```yaml
tools: Read, Bash(git:*), Bash(npm:*)
```

✅ **CORRECT** (script paths):
```yaml
tools: Read, Glob, Bash(./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)
```

❌ **INCORRECT** (array syntax even for Bash):
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

**Problem**: Including `Grep` in tools array can break Bash tool parsing when combined with parameterized Bash declarations.

**Evidence**:
- Agent with `tools: Read, Glob, Grep, Bash(./.claude/skills/script.sh:*)` reports "Bash tool not available"
- Agent with `tools: Read, Glob, Bash(./.claude/skills/script.sh:*)` works correctly

**Root Cause**: Undocumented edge case in Claude Code's frontmatter parser where Grep interferes with subsequent Bash permission parsing.

**Fix**: Remove Grep from frontmatter tools declaration.

**Workaround**: Grep can still be used in workflow instructions without frontmatter declaration.

✅ **CORRECT** (no Grep in frontmatter):
```yaml
tools: Read, Glob, Bash(./.claude/skills/script.sh:*)
```

Workflow can still use Grep:
```markdown
### Step 2: Search for patterns

Use Grep to find violations:
```
Grep: pattern="LOGGER\\.error" files="src/**/*.java"
```
```

❌ **INCORRECT** (Grep breaks Bash):
```yaml
tools: Read, Glob, Grep, Bash(./.claude/skills/script.sh:*)
```

### Issue 2: Array Syntax vs Comma-Separated

**Problem**: Many existing files use array syntax `[Read, Write]` which works but is not the documented standard.

**Why This Matters**:
- Official docs specify comma-separated format
- Array syntax may not parse correctly in all contexts
- Consistency with documentation prevents future issues

**Fix**: Convert to comma-separated format.

**Before**:
```yaml
tools: [Read, Write, Edit, Bash, Grep, Glob]
```

**After**:
```yaml
tools: Read, Write, Edit, Bash, Grep, Glob
```

### Issue 3: Task Tool in Agents

**Problem**: Agents declare `Task` tool in frontmatter.

**Why This Fails**:
- Claude Code intentionally restricts Task tool from sub-agents
- Agent will report "I don't have access to a 'Task' tool" when executed
- Architectural violation: Commands orchestrate, agents execute

**Fix**: Remove Task from agent frontmatter. If orchestration needed, use a command instead.

❌ **INCORRECT** (Task in agent):
```yaml
---
name: my-agent
tools: Read, Task
---
```

✅ **CORRECT** (use command for orchestration):
```yaml
---
name: my-command
tools: Read, Task
---

Call agent via Task tool:
```
Task:
  subagent_type: pm-plugin-development:my-agent
  description: Execute analysis
```
```

### Issue 4: Unsupported Fields in Skills

**Problem**: Skills declare `allowed-tools` or `tools` which are not supported by the plugin schema.

**Why This Fails**: The skill schema only supports: `name`, `description`, `user-invokable`, `argument-hint`, `compatibility`, `disable-model-invocation`, `license`, `metadata`. Any other field is silently ignored.

**Fix**: Remove the field entirely. Skills do not have tool declarations.

❌ **INCORRECT**:
```yaml
---
name: my-skill
description: My skill
user-invokable: true
allowed-tools: Read, Write
---
```

✅ **CORRECT**:
```yaml
---
name: my-skill
description: My skill
user-invokable: true
---
```

### Issue 5: Invalid Tool Names

**Problem**: Using tool names that don't exist or are misspelled.

**Valid Tools**:
- `Read` - Read files
- `Write` - Write files
- `Edit` - Edit files
- `Bash` - Execute bash commands
- `Grep` - Search file contents
- `Glob` - Find files by pattern
- `Task` - Invoke agents (commands only)
- `Skill` - Load skills (commands/agents only)

**Case Sensitive**: Tool names are case-sensitive. Use exact capitalization.

❌ **INCORRECT**:
```yaml
tools: read, write, bash  # lowercase
tools: READ, WRITE, BASH  # uppercase
tools: File, Search       # wrong names
```

✅ **CORRECT**:
```yaml
tools: Read, Write, Bash
```

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
```
marketplace/bundles/pm-plugin-development/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh
```

**Runtime Mount Point**:
```
./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh
```

**Why This Matters**:
1. Agents/commands use **runtime paths** in frontmatter (`./.claude/skills/...`)
2. Claude Code mounts skills when loaded
3. This is NOT a relative path to "fix" - it's the correct runtime mount point
4. Do NOT use physical marketplace paths in frontmatter

#### Bash Tool Script Permissions

When using Bash tool to execute scripts located in skills:

✅ **CORRECT frontmatter declaration**:
```yaml
tools: Read, Glob, Bash(./.claude/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)
```

❌ **INCORRECT** (physical path):
```yaml
tools: Read, Bash(./marketplace/bundles/pm-plugin-development/skills/cui-marketplace-architecture/scripts/analyze-skill-structure.sh:*)
```

❌ **INCORRECT** (absolute path):
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

✅ **CORRECT**:
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

## Quality Checklist

Use this checklist when creating or reviewing frontmatter:

**All Components** (agents, commands, skills):
- [ ] YAML frontmatter present with `---` delimiters
- [ ] `name` field present with valid pattern `^[a-z0-9-]+$`
- [ ] `description` field present with adequate length
- [ ] No blank lines in frontmatter
- [ ] Valid YAML syntax (no tabs, proper spacing)

**Agents**:
- [ ] `tools` field uses comma-separated format (not array)
- [ ] Tools list does NOT include `Task`
- [ ] Tools list does NOT include `Grep` if using parameterized `Bash`
- [ ] `description` includes input/output examples
- [ ] `model` field (if present) uses valid value: `sonnet`, `opus`, `haiku`
- [ ] `color` field (if present) uses valid color name

**Commands**:
- [ ] `tools` field uses comma-separated format (not array)
- [ ] Can include `Task` tool if orchestrating agents
- [ ] Tools list does NOT include `Grep` if using parameterized `Bash`
- [ ] `description` is user-focused (what command does, not how)

**Skills**:
- [ ] No `tools`, `allowed-tools`, `model`, or `color` fields (not supported for skills)
- [ ] **`user-invokable` field present** (either `true` or `false`, note the 'k' spelling)
- [ ] `user-invokable` value matches skill purpose (true for user-facing, false for internal)

## Reference

**Related Standards**:
- agent-quality-standards.md - Comprehensive agent quality requirements
- command-quality-standards.md - Comprehensive command quality requirements
- architecture-rules.md - Pattern 18 (Task tool restrictions), Pattern 6 (Orchestration)
- script-development.md - Bash script integration patterns

**Official Documentation**:
- Claude Code documentation: https://docs.claude.com/en/docs/claude-code/settings
- Agent SDK: https://platform.claude.com/docs/en/agent-sdk/subagents
