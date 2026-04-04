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

**Tool usage patterns** (load for file operations, content search, or automation work):
```
Read: standards/tool-usage-patterns.md
```

Covers tool selection guide, file operations (discovery, existence checks, validation), content search patterns (Grep modes, filtering), Bash safety rules (one command per call, no shell constructs, no heredocs), and build command resolution via architecture API.

## Hard Rules (never override)

### Bash: One command per call

Each Bash tool call must contain exactly ONE command. Never combine with newlines, `&`, `&&`, or `;`.

### Bash: No file operations

Never use Bash for file discovery or reading. Use Glob, Grep, Read instead.

### `.plan/` access: Scripts only

ALL `.plan/` file access MUST go through `python3 .plan/execute-script.py`. Exception: when the loaded skill's workflow explicitly documents a direct `Write(...)` or `Read(...)` call.

### Skill workflow: No improvisation

Execute ONLY the commands documented in the loaded skill's workflow. Never add discovery steps, invent arguments, or skip documented steps.

## Related

- `dev-general-code-quality` — Complementary quality standards (SRP, CQS, complexity)
- `dev-general-module-testing` — Testing methodology standards (AAA pattern, coverage)

## Standards Reference

| Standard | Purpose |
|----------|---------|
| general-development-rules.md | Boy Scout Rule, ask users, research, tool usage, dependencies |
| tool-usage-patterns.md | Tool selection, file operations, content search, Bash safety, build resolution |
