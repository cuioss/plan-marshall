# Agent Creation Guide

Guide for creating well-structured marketplace agents. For architecture principles, see `plugin-architecture` skill references.

## When to Create Agents vs Other Components

### Create an Agent When:
- **Focused execution** - Single, well-defined task (analyze code, run tests, build project)
- **Autonomous operation** - Can complete task without user interaction after launch
- **Tool usage** - Needs specific tools to accomplish task
- **Reusable logic** - Task will be performed multiple times across workflows

### Create a Command Instead When:
- **User interaction required** - Need to ask questions or gather requirements
- **Orchestration needed** - Coordinating multiple agents or complex workflows
- **Delegation required** - Need to launch other agents using Task tool

### Create a Skill Instead When:
- **Knowledge provision** - Providing standards, guidelines, or reference material
- **No execution** - Just documentation to be loaded, not actions to perform

## Agent Design Principles

### Focused Executors
Agents do ONE task well. Don't create "swiss army knife" agents.

### Self-Contained
Agents must be self-contained with clear input/output contracts — document expected inputs, produced outputs, and list all required tools in frontmatter.

### Clear Workflow
Agents must have numbered workflow steps that are easy to follow.

### MANDATORY Markers
Use MANDATORY markers for critical steps (script execution, validation gates). See `plugin-architecture:execution-directive` for patterns and usage guidance. Limit to 2-3 per workflow.

## Frontmatter Format

See `plugin-architecture:frontmatter-standards` for the complete specification.

```yaml
---
name: agent-name          # kebab-case, descriptive
description: One sentence  # <100 chars, clear purpose
tools: Read, Write, Edit   # Comma-separated (NOT array)
model: sonnet              # Optional: haiku, sonnet, opus
---
```

**Key Rules**:
- **tools**: Comma-separated (NOT array syntax `[Read, Write]`)
- **No Task tool** — agents can't delegate (see Critical Rules below)
- **No SlashCommand** — unavailable at runtime

## Critical Rules

### Rule 6: Agents CANNOT Use Task Tool

Task tool is unavailable to agents at runtime. If agent needs delegation, create a **Command** instead — commands orchestrate agents via Task tool.

### Rule 7: Only maven-builder Agent Can Execute Maven

Centralized build execution prevents scattered Maven calls. If your agent needs build results, it should analyze and return results to caller, which orchestrates maven-builder if needed.

### Lessons via manage-lessons Skill

Agents record lessons through `Skill: plan-marshall:manage-lessons`, not through self-update patterns.

## Agent Structure Template

```markdown
---
name: agent-name
description: One sentence description (<100 chars)
model: optional_model
tools: Tool1, Tool2, Tool3
---

# Agent Name

Purpose statement explaining what this agent does.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "agent", name: "{agent_name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## Workflow

### Step 1: [First Action]
[Description]

### Step 2: [Second Action]
[Description]

## Tool Usage

[Explanation of how each tool is used]

## Critical Rules

[List critical rules agent must follow]
```

## Resource Mode Labeling

Agents with scripts and references should clearly label each resource's mode:

| Mode | Meaning |
|------|---------|
| **EXECUTE** | Run this script/tool immediately as part of workflow |
| **READ** | Load this file's content into context |
| **REFERENCE** | Consult on-demand when specific information needed |

## Tool Selection Guidelines

- **Read, Write, Edit, Glob, Grep** — Core file operations (prefer over Bash equivalents)
- **Bash** — For git operations, build commands, shell operations
- **NEVER Task** — Agents can't delegate (Rule 6)
- **NEVER SlashCommand** — Unavailable at runtime
- **AskUserQuestion** — Rare in agents (usually in commands)

## Validation Checklist

Before creating agent, verify:

- Single, focused purpose
- Name is kebab-case and descriptive
- Description is <100 chars
- Tools list is comma-separated (not array)
- No Task tool included
- If Bash tool: Not calling Maven (unless maven-builder)
- CONTINUOUS IMPROVEMENT RULE uses manage-lessons skill
- Workflow has numbered steps
- Input/output contracts clear

For complete quality rules, see `plugin-doctor:agents-guide`.

## References

- Architecture Rules: See `plugin-architecture` skill
- Frontmatter Spec: See `plugin-architecture:frontmatter-standards`
- Execution Directives: See `plugin-architecture:execution-directive`
- Quality Validation: See `plugin-doctor:agents-guide`
