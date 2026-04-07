---
name: ext-triage-python
description: Triage extension for Python findings during plan-finalize phase
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-triage
---

# Python Triage Extension

Provides decision-making knowledge for triaging Python findings during the finalize phase.

## Purpose

This skill is a **triage extension** loaded by the plan-finalize workflow skill when processing Python-related findings. It provides domain-specific knowledge for deciding whether to fix, suppress, or accept findings.

**Key Principle**: This skill provides **knowledge**, not workflow control. The finalize skill owns the process.

## When This Skill is Loaded

Loaded via `resolve-workflow-skill-extension --domain python --type triage` during finalize phase when:

1. Ruff reports linting or formatting violations
2. Mypy reports type-checking errors
3. Pytest failures or coverage regressions occur
4. PR review comments reference Python code quality
5. Pyprojectx build errors are flagged

## Standards

| Document | Purpose |
|----------|---------|
| [suppression.md](standards/suppression.md) | Python-specific suppression syntax (ruff, mypy, pytest) |
| [severity.md](standards/severity.md) | Python-specific severity guidelines and decision criteria |

## Extension Registration

Registered in marshal.json under the python domain:

```json
"python": {
  "workflow_skill_extensions": {
    "triage": "pm-dev-python:ext-triage-python"
  }
}
```

## Quick Reference

### Suppression Methods

| Finding Type | Syntax |
|--------------|--------|
| Ruff rule (inline) | `# noqa: E501` |
| Ruff rule (file) | `# ruff: noqa: E501` at top of file |
| Ruff global | `[tool.ruff.lint.per-file-ignores]` in pyproject.toml |
| Mypy error (inline) | `# type: ignore[assignment]` |
| Mypy global | `[[tool.mypy.overrides]]` in pyproject.toml |
| Pytest skip | `@pytest.mark.skip(reason="...")` |
| Pytest expected fail | `@pytest.mark.xfail(reason="...")` |

### Decision Guidelines

| Severity | Default Action |
|----------|----------------|
| Mypy error | **Fix** (type safety violation) |
| Ruff error (E/F) | **Fix** (syntax or logic error) |
| Ruff warning (W) | Fix or suppress with justification |
| Ruff convention (C/D) | Fix or accept based on context |
| Pytest failure | **Fix** (broken behavior) |
| Coverage regression | Fix (add missing tests) or justify gap |

### Acceptable to Accept

- Type ignores for dynamic patterns (plugin systems, metaprogramming)
- Ruff suppressions in generated or vendored code
- Convention warnings in legacy code with migration plan
- Expected test failures for known upstream bugs (with issue link)
- Coverage gaps in platform-specific or error-recovery paths

## Related Documents


- `pm-dev-python:python-core` - Core Python development standards
