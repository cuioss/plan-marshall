---
name: dev-general-code-quality
description: Language-agnostic code quality principles covering SRP, CQS, complexity thresholds, refactoring triggers, error handling, and documentation standards
user-invocable: false
---

# Code Quality and Documentation Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Language-agnostic code quality and documentation principles applicable across all technology stacks. Covers design principles, complexity management, refactoring triggers, error handling, and API documentation.

## Workflow

### Step 1: Load Code Organization Standards

**Important**: Load this standard for any implementation or refactoring work.

```
Read: standards/code-organization.md
```

Covers SRP, CQS, parameter objects, package structure, immutability, refactoring triggers, complexity thresholds, and maintenance prioritization.

### Step 2: Load Additional Standards (As Needed)

**Error Handling** (load for error/exception work):
```
Read: standards/error-handling.md
```

Use when: Designing error handling, exception hierarchies, or recovery patterns.

**Documentation Principles** (load for API documentation work):
```
Read: standards/documentation-principles.md
```

Use when: Writing or reviewing public API documentation, updating docs during code changes.

## Related Skills

- `pm-dev-java:java-core` — Java-specific patterns and features
- `pm-dev-java:java-maintenance` — Java maintenance prioritization
- `pm-dev-java:javadoc` — JavaDoc tag syntax and Java-specific patterns
- `pm-dev-frontend:javascript` — JavaScript-specific patterns including JSDoc

## Code Examples

### Single Responsibility — Before
```python
class UserService:
    def create_user(self, data):
        # validates, saves to DB, sends email, logs audit
        ...
```

### Single Responsibility — After
```python
class UserService:
    def __init__(self, repo, notifier):
        self._repo = repo
        self._notifier = notifier

    def create_user(self, data):
        user = self._repo.save(data)
        self._notifier.welcome(user)
        return user
```

## Standards Reference

| Standard | Purpose |
|----------|---------|
| code-organization.md | SRP, CQS, package structure, refactoring triggers, complexity, maintenance |
| error-handling.md | Exception philosophy, propagation, recovery |
| documentation-principles.md | What/when/how to document public APIs |
