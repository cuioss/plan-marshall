---
name: ext-triage-js
description: Triage extension for JavaScript findings during plan-finalize phase
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-triage
---

# JavaScript Triage Extension

Provides decision-making knowledge for triaging JavaScript findings during the finalize phase.

## Purpose

This skill is a **triage extension** loaded by the plan-finalize workflow skill when processing JavaScript-related findings. It provides domain-specific knowledge for deciding whether to fix, suppress, or accept findings.

**Key Principle**: This skill provides **knowledge**, not workflow control. The finalize skill owns the process.

## When This Skill is Loaded

Loaded via `resolve-workflow-skill-extension --domain javascript --type triage` during finalize phase when:

1. ESLint reports rule violations
2. Jest test failures occur
3. Prettier formatting issues are detected
4. Stylelint reports CSS issues

## Standards

| Document | Purpose |
|----------|---------|
| [suppression.md](standards/suppression.md) | JavaScript suppression syntax (eslint-disable) |
| [severity.md](standards/severity.md) | JavaScript-specific severity guidelines and decision criteria |

## Quick Reference

### Suppression Methods

| Finding Type | Syntax |
|--------------|--------|
| ESLint rule | `// eslint-disable-next-line rule-name` |
| ESLint block | `/* eslint-disable rule-name */` |
| Prettier | Not suppressible (fix or configure) |
| Stylelint | `/* stylelint-disable rule-name */` |

### Decision Guidelines

| Severity | Default Action |
|----------|----------------|
| error | **Fix** (blocks build/CI) |
| warn | Fix or suppress with justification |
| off | N/A (disabled rule) |

### Acceptable to Accept

- Generated code in `**/generated/**`, `**/dist/**`
- Legacy JavaScript files with tracked plan to address
- Test mocks requiring flexibility

## Related Documents


- `pm-dev-frontend:javascript` - Core JavaScript patterns
