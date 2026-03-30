---
name: plugin-create
description: Create new marketplace components (agents, commands, skills, bundles) with proper structure and standards compliance
user-invocable: true
---

# Plugin Create Skill

Interactive wizard for creating well-structured marketplace components following architecture best practices.

## Enforcement

**Execution mode**: Interactive wizard — gather user input via AskUserQuestion, validate, generate, verify.

**Prohibited actions:**
- Agents cannot use the Task tool (Rule 6 — unavailable at runtime). If user lists `Task` in tools, reject and suggest creating a command instead.
- Only maven-builder agent may execute Maven commands (Rule 7). If a non-maven-builder agent needs Bash and Maven, reject.
- Do not invent script notations — use only documented notations

**Constraints:**
- Use comma-separated format for frontmatter tools: `tools: Read, Write, Edit` (not array syntax)
- All questionnaire responses are validated with clear error messages and retry prompts
- Check for duplicates before creating any component
- Load reference guides on-demand (never load all at once); use relative paths for all resources
- Agents and commands use manage-lessons skill for the CONTINUOUS IMPROVEMENT RULE section; skills do not have this section
- Each workflow step that performs a script operation has an explicit bash code block with the full `python3 .plan/execute-script.py` command

## What This Skill Provides

**Component Creation**: Unified workflows for creating agents, commands, skills, and bundles with proper structure, frontmatter, and standards compliance.

**Validation**: Automated validation of component structure, frontmatter format, and architecture compliance.

**Templates**: Consistent templates for all component types with proper sections and formatting.

**Duplication Detection**: Prevents creating duplicate components by checking existing components in target bundle.

## Pattern Type

**Pattern 5 + Pattern 6**: Wizard-Style Workflow + Template-Based Generation

- Pattern 5: Interactive questionnaires with validation
- Pattern 6: Fill templates with user answers and generate files

## When to Use This Skill

Activate when creating:
- **New agents** - Focused task executors
- **New commands** - User-facing utilities and orchestrators
- **New skills** - Standards and knowledge repositories
- **New bundles** - Component collections with plugin.json

## Workflows

This skill provides 4 workflows, one for each component type. All workflows follow the same pattern:
1. Interactive questionnaire with validation
2. Duplication detection
3. Generate component from template
4. Validate generated component
5. Display summary with statistics
6. Run post-creation diagnosis

Load the relevant workflow on-demand based on the component type being created.

### Workflow 1: create-agent

```
Read standards/workflow-create-agent.md
```

Creates a new agent with proper frontmatter, tool selection, Rule 6/7 enforcement, and CONTINUOUS IMPROVEMENT RULE.

### Workflow 2: create-command

```
Read standards/workflow-create-command.md
```

Creates a new command with thin orchestrator pattern, parameter design, and CONTINUOUS IMPROVEMENT RULE.

### Workflow 3: create-skill

```
Read standards/workflow-create-skill.md
```

Creates a new skill with directory structure, SKILL.md, README, and placeholder standards files.

### Workflow 4: create-bundle

```
Read standards/workflow-create-bundle.md
```

Creates a new bundle with plugin.json, directory structure, and optional initial components (delegates to workflows 1-3).

## References

This skill uses the following reference files (load on-demand):

### Agent Creation
- **references/agent-guide.md** - Agent design principles, tool selection, architecture rules

### Command Creation
- **references/command-guide.md** - Command design principles, quality standards, orchestration patterns

### Skill Creation
- **references/skill-guide.md** - Skill patterns, resource organization, progressive disclosure

### Bundle Creation
- **references/bundle-guide.md** - Bundle structure, plugin.json configuration, naming conventions

## Scripts

Script: `pm-plugin-development:plugin-create` → `component.py`

| Subcommand | Purpose |
|------------|---------|
| `validate` | Validates marketplace component structure |
| `generate` | Generates YAML frontmatter for components |

### component.py validate
**Purpose**: Validates marketplace component structure

**Usage**:
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component validate --file <file_path> --type <component_type>
```

**Output**: JSON with validation results

### component.py generate
**Purpose**: Generates YAML frontmatter for components

**Usage**:
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component generate --type <component_type> --config '<answers_json>'
```

**Output**: Formatted YAML frontmatter string

## Templates

This skill uses the following templates in assets/templates/:

- **agent-template.md** - Template for new agents
- **command-template.md** - Template for new commands
- **skill-template.md** - Template for new skills (SKILL.md)
- **bundle-structure.json** - Bundle directory structure template

## Rule Definitions

Rules applied during component creation. See Enforcement block for this skill's own constraints.

**Frontmatter Format**:
- Use comma-separated format for tools: `tools: Read, Write, Edit`
- Do not use array syntax: `tools: [Read, Write, Edit]`

**Tool Prohibitions**:
- Agents cannot use Task tool (Rule 6) — unavailable at runtime
- Only maven-builder agent can execute Maven (Rule 7)

**Continuous Improvement Rule**:
- Agents: Use manage-lessons skill to record lessons (report to caller)
- Commands: Use manage-lessons skill to record lessons
- Skills: No Continuous Improvement Rule section

**Validation**:
- All questionnaire responses are validated
- Clear error messages with retry prompts
- Check for duplicates before creating

**Progressive Disclosure**:
- Load reference guides on-demand (not all at once)
- Use relative paths for all resources

## Quality Standards

Following these ensures:
- Consistent component structure across marketplace
- Proper frontmatter formatting
- Architecture compliance
- No duplicate components
- Validated creation with post-diagnosis
- Statistics tracking for transparency
