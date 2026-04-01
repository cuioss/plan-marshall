---
name: dev-general-practices
description: Foundational development practices covering user interaction, tool usage, research, dependency management, and document proliferation
user-invocable: false
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

Covers Boy Scout Rule, decision tree for when to ask users, research patterns, tool selection guide, document proliferation guidelines, and dependency approval.

### Step 2: Load Tool Usage Standards (As Needed)

**Tool usage patterns** (load for diagnostic/automation work):
```
Read: standards/tool-usage-patterns.md
```

Covers tool selection guide, Bash safety rules (one command per call, no shell constructs, no heredocs), build command resolution via architecture API.

**File operations** (load for file system work):
```
Read: standards/file-operations.md
```

Covers file discovery, existence checks, content validation using Glob/Read.

**Search operations** (load for content analysis):
```
Read: standards/search-operations.md
```

Covers content search, pattern matching, reference validation using Grep.

## Hard Rules (never override)

### Bash: One command per call

Each Bash tool call must contain exactly ONE command. Never combine with newlines, `&`, `&&`, or `;`.

### Bash: No file operations

Never use Bash for file discovery or reading. Use Glob, Grep, Read instead.

### `.plan/` access: Scripts only

ALL `.plan/` file access MUST go through `python3 .plan/execute-script.py`. Exception: when the loaded skill's workflow explicitly documents a direct `Write(...)` or `Read(...)` call.

### Skill workflow: No improvisation

Execute ONLY the commands documented in the loaded skill's workflow. Never add discovery steps, invent arguments, or skip documented steps.

## Related Skills

- `plan-marshall:dev-general-code-quality` — Code quality, refactoring, and documentation principles
- `plan-marshall:dev-general-module-testing` — Testing methodology

## Standards Reference

| Standard | Purpose |
|----------|---------|
| general-development-rules.md | Boy Scout Rule, ask users, research, tool usage, dependencies |
| tool-usage-patterns.md | Tool selection, Bash safety rules, build resolution |
| file-operations.md | File discovery, existence checks, content validation |
| search-operations.md | Content search, pattern matching, result parsing |
