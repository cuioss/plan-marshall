# Command Creation Guide

Guide for creating well-structured marketplace commands following the thin orchestrator pattern. For the full pattern specification, see `plugin-architecture:minimal-wrapper-pattern`.

## When to Create Commands vs Other Components

### Create a Command When:
- **User-facing utility** - Users invoke directly with `/command-name`
- **Interactive workflow** - Need to ask user questions or gather requirements
- **Orchestration** - Coordinating multiple agents or workflows
- **Parameter routing** - Parse parameters and route to appropriate workflows
- **Delegation** - Need to use Task tool to launch agents

### Create an Agent Instead When:
- **Autonomous execution** - No user interaction after launch
- **Focused task** - Single, well-defined operation

### Create a Skill Instead When:
- **Knowledge provision** - Standards, guidelines, reference material
- **No user invocation** - Loaded by commands/agents, not run directly

## Command Design Principles

### Thin Orchestrators
Commands parse parameters and route to skills/agents. They do NOT contain embedded logic. Target <400 lines. See `plugin-architecture:minimal-wrapper-pattern` for thresholds and migration patterns.

### Parameter-Driven
Commands parse parameters and make routing decisions:

```markdown
## PARAMETERS

**scope** - What to analyze (agent/command/skill/all, default: all)
**name** - Specific component name (optional)
**fix** - Auto-fix issues (true/false, default: false)
```

### Skill Delegation with Critical Handoff

Commands delegate heavy lifting to skills, but must include explicit handoff rules to ensure Claude EXECUTES the skill rather than explaining it. See `plugin-architecture:execution-directive` for the full pattern.

**Required pattern** — every command that loads a skill:
```markdown
Skill: bundle-name:skill-name

**CRITICAL HANDOFF RULES**:
- DO NOT summarize or explain the skill content to the user
- IMMEDIATELY execute the scripts and tools specified in the skill
- Your next action after loading the skill MUST be a tool call, not text output
```

## Frontmatter Format

See `plugin-architecture:frontmatter-standards` for the complete specification.

```yaml
---
name: command-name
description: One sentence description (<100 chars)
tools: Read, Bash, Skill
---
```

- **tools**: Comma-separated (NOT array syntax)
- Commands CAN include `Task` tool for agent orchestration
- Name must be kebab-case

## Required Sections

Every command must have:
1. **Frontmatter** (YAML with name, description)
2. **Title** (# Command Name)
3. **Overview** (brief explanation)
4. **CONTINUOUS IMPROVEMENT RULE**
5. **PARAMETERS** (if applicable)
6. **WORKFLOW** (numbered steps)
7. **CRITICAL RULES**
8. **USAGE EXAMPLES**
9. **RELATED** (related commands/skills)

## CONTINUOUS IMPROVEMENT RULE for Commands

```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "{command-name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```

## Workflow Patterns

### Direct Skill Routing
```
Command → Load Skill → Execute Workflow → Display Results
```

### Conditional Routing
```
Command → Parse Parameters → Route to Different Workflows → Display
```

### Sequential Orchestration
```
Command → Workflow 1 → Workflow 2 → Verify → Display
```

### Agent Delegation
```
Command → Launch Agent(s) via Task → Aggregate Results → Display
```

## Error Handling Patterns

- **Validate Early**: Check parameters in Step 1, fail early
- **Graceful Degradation**: Show warning, continue (don't abort entire command)
- **User Recovery**: Offer retry/abort options for write failures

## Validation Checklist

Before creating command, verify:

- Name is kebab-case with verb (create-agent, run-tests)
- Description is <100 chars
- Tools field is comma-separated
- CONTINUOUS IMPROVEMENT RULE uses manage-lessons skill
- Workflow is numbered steps
- Command is <400 lines
- No embedded templates — delegates to skills
- Error handling specified

For complete quality rules, see `plugin-doctor:commands-guide`.

## References

- Thin Orchestrator Pattern: See `plugin-architecture:minimal-wrapper-pattern`
- Skill Delegation: See `plugin-architecture:execution-directive`
- Frontmatter Spec: See `plugin-architecture:frontmatter-standards`
- Quality Validation: See `plugin-doctor:commands-guide`
