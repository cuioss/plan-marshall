---
name: dev-general-code-documentation
description: Language-agnostic code documentation principles covering what, when, and how to document public APIs
user-invocable: false
---

# Code Documentation Principles Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Language-agnostic documentation principles applicable across all technology stacks. This skill covers what to document, documentation quality, and maintainability.

## Workflow

### Step 1: Load Documentation Principles

**Important**: Load this standard for any documentation work.

```
Read: standards/documentation-principles.md
```

This provides foundational rules for:
- Mandatory documentation requirements (what must be documented)
- Clarity and purpose (WHAT and WHY, not implementation)
- Completeness (parameters, returns, exceptions)
- Consistency and maintainability
- What NOT to document (anti-patterns)

## Key Rules Summary

### Boy Scout Rule

Leave documentation cleaner than you found it. When modifying a file, fix existing documentation issues you encounter — outdated descriptions, missing parameter docs, stale cross-references. Never dismiss incorrect documentation with "not introduced by current changes" — always fix it. If fixes cascade beyond reasonable scope, stop and ask the user how to proceed.

### Mandatory Documentation

- All public/exported APIs (classes, functions, methods)
- All parameters with meaningful descriptions
- Return values with what they represent
- Exceptions/errors with when they occur
- Code examples for complex APIs

### Documentation Quality

- **Stay focused and crisp** — convey core aspects with minimal text, never be verbose
- Explain WHAT the code does and WHY it exists
- Never state the obvious or repeat the function name
- Document the contract, not the implementation
- Keep docs synchronized with code changes

### What NOT to Document

- Trivial getters/setters without business logic
- Private methods (unless complex)
- Methods that simply delegate without logic
- Obvious field declarations

## Related Skills

- `pm-dev-java:javadoc` — JavaDoc tag syntax and Java-specific patterns
- `pm-dev-frontend:javascript` — JavaScript standards including JSDoc

## Standards Reference

| Standard | Purpose |
|----------|---------|
| documentation-principles.md | What/when/how to document, clarity, completeness |
