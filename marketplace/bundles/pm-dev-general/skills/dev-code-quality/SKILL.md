---
name: dev-code-quality
description: Language-agnostic code quality principles covering SRP, CQS, complexity thresholds, refactoring triggers, and error handling
user-invocable: false
---

# Code Quality Principles Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Language-agnostic code quality principles applicable across all technology stacks. This skill covers design principles, complexity management, refactoring triggers, and error handling.

## Workflow

### Step 1: Load Code Organization Standards

**Important**: Load this standard for any implementation or refactoring work.

```
Read: standards/code-organization.md
```

This provides foundational rules for:
- Single Responsibility Principle
- Command-Query Separation
- Parameter objects when count hurts readability (language-dependent threshold)
- Package/module structure (feature-based)
- Immutability preference

### Step 2: Load Additional Standards (As Needed)

**Refactoring Triggers** (load for code analysis/maintenance):
```
Read: standards/refactoring-triggers.md
```

Use when: Identifying when code needs refactoring based on metrics and patterns.

**Error Handling** (load for error/exception work):
```
Read: standards/error-handling.md
```

Use when: Designing error handling, exception hierarchies, or recovery patterns.

## Key Rules Summary

### Boy Scout Rule

Leave code cleaner than you found it. When modifying a file, fix existing quality issues you encounter — poor naming, SRP violations, dead code, missing error handling. Never dismiss code smells with "not introduced by current changes" — always fix them. If fixes cascade beyond reasonable scope, stop and ask the user how to proceed.

### Design Principles

- **Single Responsibility** — each class/module/function does one thing
- **Command-Query Separation** — methods either modify state (command) or return data (query), not both
- **Parameter objects** — group related parameters into objects when count becomes unwieldy (threshold varies by language)
- **Composition over inheritance** — prefer delegation
- **Immutability** — prefer immutable data structures

### Complexity Thresholds

- Method/function length: prefer < 50 lines
- Cyclomatic complexity: max 15
- Nesting depth: max 3 levels
- Parameters: reduce when count hurts readability (language-dependent)

### Refactoring Triggers

- Method exceeds length or complexity threshold
- Class has multiple unrelated responsibilities
- Duplicated code across methods/classes
- Deep nesting or complex boolean expressions

### Error Handling

- Use specific exception/error types, never generic
- Include meaningful error messages with context
- Preserve error causes with chaining
- Use guard clauses and early returns

## Related Skills

- `pm-dev-java:java-core` — Java-specific patterns and features
- `pm-dev-java:java-maintenance` — Java maintenance prioritization
- `pm-dev-frontend:cui-javascript` — JavaScript-specific patterns

## Standards Reference

| Standard | Purpose |
|----------|---------|
| code-organization.md | SRP, CQS, package structure, parameter objects |
| refactoring-triggers.md | Complexity thresholds, method length, triggers |
| error-handling.md | Exception philosophy, propagation, recovery |
