---
name: ext-triage-python
description: Triage extension for Python findings during plan-finalize phase
user-invocable: false
mode: knowledge
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
6. PR review comment disposition is required (FIX, REPLY-AND-RESOLVE, or ESCALATE on bot review threads)
7. The Python arch-gate (import-linter) emits `arch-constraint` findings for structural-boundary violations

## Standards

| Document | Purpose |
|----------|---------|
| [suppression.md](standards/suppression.md) | Python-specific suppression syntax (ruff, mypy, pytest) |
| [severity.md](standards/severity.md) | Python-specific severity guidelines and decision criteria |
| [pr-comment-disposition.md](standards/pr-comment-disposition.md) | PR review comment disposition (FIX / REPLY-AND-RESOLVE / ESCALATE) for Python |

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

### arch-constraint Findings (import-linter arch-gate)

The Python arch-gate runs import-linter's whole-graph import contracts as a dedicated invocation and emits one `arch-constraint`-typed finding per structural-boundary violation (a directional import contract, a layered-architecture contract, a forbidden-module dependency), carrying the violated contract's identity in the finding's `rule` field. These findings route here for the per-finding disposition exactly as `lint-issue` / `sonar-issue` findings do:

| Disposition | When |
|-------------|------|
| **Fix** | The violation is a genuine structural-boundary breach — correct the import direction, invert the dependency, or remove the forbidden import. This is the default for an `arch-constraint` finding. |
| **Suppress** | The contract does not apply to this specific case and the exception is documented — narrow the import-linter contract (e.g. `ignore_imports`) with justification. |
| **Accept** | The contract itself is wrong or a known false positive — the finding is acknowledged without code change; recurring acceptances signal the contract needs revision. |

A violation of the **same contract** that recurs across runs reinforces a single `arch-constraint` lesson (rule-identity dedup; retire-on-quiet / reinforce-on-recurrence), surfaced to planning through the architecture-hints pipe. The structural model and the full findings → triage → lesson loop are owned by the central standard — see [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) and the Python binding in [`pm-dev-python:arch-gate-python`](../arch-gate-python/SKILL.md).

## Related Documents


- `pm-dev-python:python-core` - Core Python development standards
