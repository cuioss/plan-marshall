---
name: plugin-create
description: Create new marketplace components (agents, commands, skills, bundles) with proper structure and standards compliance
user-invocable: true
mode: workflow
---

# Plugin Create Skill

Interactive wizard for creating well-structured marketplace components following architecture best practices.

## Enforcement

**Execution mode**: Interactive wizard — gather user input via AskUserQuestion, validate, generate, verify.

**Prohibited actions:**
- Agents cannot use the Task tool (Rule 6 — unavailable at runtime). If user lists `Task` in tools, reject and suggest creating a command instead.
- Only the maven-builder agent may execute Maven build commands (Rule 7).
- Reject any non-maven-builder agent whose declared capabilities combine the shell tool with direct Java-build-tool invocation needs.
- Do not invent script notations — use only documented notations

**Constraints:**
- Use comma-separated format for frontmatter tools: `tools: Read, Write, Edit` (not array syntax)
- All questionnaire responses are validated with clear error messages and retry prompts
- Check for duplicates before creating any component
- Load reference guides on-demand (never load all at once); use relative paths for all resources
- Agents and commands use manage-lessons skill for the CONTINUOUS IMPROVEMENT RULE section; skills do not have this section
- Each workflow step that performs a script operation has an explicit bash code block with the full `python3 .plan/execute-script.py` command

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `component` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

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

```text
Read standards/workflow-create-agent.md
```

Creates a new agent with proper frontmatter, tool selection, Rule 6/7 enforcement, and CONTINUOUS IMPROVEMENT RULE.

### Workflow 2: create-command

```text
Read standards/workflow-create-command.md
```

Creates a new command with thin orchestrator pattern, parameter design, and CONTINUOUS IMPROVEMENT RULE.

### Workflow 3: create-skill

```text
Read standards/workflow-create-skill.md
```

Creates a new skill with directory structure, SKILL.md, README, and placeholder standards files.

### Workflow 4: create-bundle

```text
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

See Enforcement block above for all rules applied during component creation.

## Canonical invocations

The canonical argparse surface for `component.py` (the skill's argparse CLI entry-point; `cmd_generate.py` and `cmd_validate.py` are internal command-handler modules imported by `component.py`, not standalone argparse CLIs). The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### generate

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component generate \
  --type {agent,command,skill} --config CONFIG
```

### validate

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component validate \
  --file FILE --type {agent,command,skill}
```
