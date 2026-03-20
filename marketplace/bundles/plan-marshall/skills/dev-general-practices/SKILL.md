---
name: dev-general-practices
description: Foundational development practices covering user interaction, tool usage, research, dependency management, and document proliferation
user-invocable: false
standards:
  - standards/general-development-rules.md
  - standards/file-operations.md
  - standards/search-operations.md
  - standards/tool-usage-patterns.md
---

# Development Practices Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Foundational development practices applicable across all technology stacks and development activities. Covers when to ask users, how to research best practices, proper tool usage, document management, and dependency governance.

## Workflow

### Step 1: Load Core Development Rules

**Important**: Load this standard at the start of any development work.

```
Read: standards/general-development-rules.md
```

This provides:
- Decision tree for when to ask users vs proceed autonomously
- Research patterns using research-best-practices-agent
- Tool selection guide (Read/Write/Edit/Glob/Grep over Bash equivalents)
- Document proliferation guidelines
- Dependency approval requirements

### Step 2: Load Tool Usage Standards (As Needed)

**Tool usage patterns** (load for diagnostic/automation work):
```
Read: standards/tool-usage-patterns.md
```

Use when: Building automated workflows, diagnostic commands, or agent implementations.

**File operations** (load for file system work):
```
Read: standards/file-operations.md
```

Use when: Implementing file discovery, existence checks, or content validation patterns.

**Search operations** (load for content analysis):
```
Read: standards/search-operations.md
```

Use when: Implementing content search, pattern matching, or integration validation.

## Hard Rules (never override)

These rules apply to ALL tool calls. Violations trigger user permission prompts and block execution.

### Bash: One command per call

Each Bash tool call must contain exactly ONE command. NEVER:
- Combine commands with newlines, `&`, `&&`, or `;`
- Use `python3 -c "..."` with inline multiline scripts
- Use `2>&1 &` to background commands

If two commands are independent, make two separate Bash calls.

### Bash: No file operations

NEVER use Bash for file discovery or reading. Use dedicated tools:
- `find`, `ls` → use **Glob** tool
- `grep`, `rg` → use **Grep** tool
- `cat`, `head`, `tail` → use **Read** tool

### `.plan/` access: Scripts only

ALL `.plan/` file access MUST go through `python3 .plan/execute-script.py`. NEVER:
- Read/Write/Edit any `.plan/**` file directly
- Use `python3 -c` to parse `.plan/` JSON/TOON files
- Use Bash to cat/grep `.plan/` files

### Skill workflow: No improvisation

Execute ONLY the commands documented in the loaded skill's workflow. NEVER:
- Add discovery steps not in the skill
- Invent script arguments (e.g., `--field all`)
- Substitute a different command for one documented in the skill
- Skip steps documented in the skill (including phase transitions)

## Key Rules Summary

### Ask When In Doubt

Never guess or be creative. If uncertain about requirements, ask the user for guidance. When multiple valid approaches exist, present options rather than choosing arbitrarily.

### Research Current Best Practices

Use research-best-practices-agent for finding latest recommendations. Do not rely on outdated knowledge or use unstructured web searches directly.

### Don't Proliferate Documents

Search for existing documents before creating new ones. Only create new documents with explicit user approval.

### Get Dependency Approval

Never add dependencies without user approval. Present recommendations with rationale and wait for confirmation.

## Related Skills

- `plan-marshall:dev-general-code-quality` — Code quality principles (SRP, CQS, complexity)
- `plan-marshall:dev-general-code-documentation` — Documentation principles
- `plan-marshall:dev-general-module-testing` — Testing methodology

## Standards Reference

| Standard | Purpose |
|----------|---------|
| general-development-rules.md | Core principles: ask users, research, tool usage, dependencies |
| file-operations.md | File discovery, existence checks, content validation patterns |
| search-operations.md | Content search, pattern matching, result parsing |
| tool-usage-patterns.md | Tool selection guide, non-prompting alternatives |
