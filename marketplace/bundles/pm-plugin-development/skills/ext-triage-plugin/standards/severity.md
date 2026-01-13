# Plugin Development Severity Guidelines

Decision criteria for handling marketplace plugin development findings.

## Finding Sources

| Source | Description |
|--------|-------------|
| pytest | Python script test failures |
| plugin-doctor | Marketplace component quality |
| markdownlint | Documentation formatting |
| yamllint | YAML configuration validation |
| mypy/pyright | Python type checking |

## Decision by Source

### Pytest Failures

| Type | Action | Notes |
|------|--------|-------|
| Assertion failure | **Fix** | Test or code is wrong |
| Import error | **Fix** | Missing dependency or path |
| Timeout | Fix or increase | Check for performance issue |
| Skip (with reason) | Accept | Document why skipped |
| xfail | Accept | Known issue tracked |

### Plugin-Doctor Issues

| Severity | Action | Notes |
|----------|--------|-------|
| Critical (structure) | **Fix** | Component won't load |
| Error (frontmatter) | **Fix** | Required fields missing |
| Warning (content) | Fix preferred | Quality improvement |
| Info (style) | Accept | Low impact |

### Markdown Linting

| Category | Action | Notes |
|----------|--------|-------|
| Heading structure | Fix | Navigation and parsing |
| Line length (MD013) | Accept in tables | Configure limit |
| Inline HTML (MD033) | Case by case | Sometimes necessary |
| First line heading | Accept | Frontmatter files |

### Python Type Errors

| Context | Action | Notes |
|---------|--------|-------|
| New code | **Fix** | Add proper types |
| Dynamic patterns | Suppress | Document limitation |
| Third-party stubs | Suppress | External dependency |
| stdlib-only code | Fix | No complex dependencies |

## Context Modifiers

### Script Criticality

| Script Type | Standard |
|-------------|----------|
| Core script (manage-*.py) | Strict - fix all issues |
| Utility script | Normal - fix errors |
| Experimental script | Lenient - suppress with plan |

### Documentation Type

| Doc Type | Standard |
|----------|----------|
| SKILL.md | Strict - primary interface |
| Standards (*.md) | Normal - consistency |
| References | Normal - accuracy |
| Examples | Lenient - readability over rules |

## Acceptable to Accept

### Always Acceptable

| Finding | Reason |
|---------|--------|
| Line length in tables | Tables can't wrap |
| Line length in URLs | URLs can't break |
| MD041 with frontmatter | Frontmatter before heading |
| Test skip with reason | Documented exception |

### Conditionally Acceptable

| Finding | Condition |
|---------|-----------|
| Type ignore | Documented limitation |
| xfail test | Tracked in issue |
| Plugin-doctor warning | Experimental component |

### Never Acceptable

| Finding | Reason |
|---------|--------|
| Test failure without skip | Quality gate |
| Plugin-doctor critical | Component broken |
| Import error | Won't execute |
| YAML syntax error | Invalid configuration |

## Quick Decision Flowchart

```
Is it a test failure?
  → Yes, can be fixed → FIX
  → Yes, environment-specific → SKIP with reason
  → Yes, known bug → XFAIL with issue reference

Is it plugin-doctor critical?
  → Yes → FIX (component won't work)

Is it plugin-doctor error?
  → Yes → FIX (required for quality)

Is it a type error?
  → Yes, in new code → FIX
  → Yes, dynamic pattern → SUPPRESS with explanation

Is it markdown lint?
  → Table/URL related → ACCEPT or configure
  → Structure issue → FIX

Else → FIX if low effort, ACCEPT otherwise
```

## Iteration Limits

| Iteration | Focus |
|-----------|-------|
| 1 | Fix all test failures, critical issues |
| 2 | Fix plugin-doctor errors, type errors |
| 3 | Fix warnings, documentation issues |
| MAX (5) | Accept remaining with documentation |

## Quality Gate Summary

Before completing finalize phase:

| Requirement | Threshold |
|-------------|-----------|
| pytest | All pass (or documented skip/xfail) |
| plugin-doctor | No critical/error issues |
| Type checking | No errors (ignores documented) |
| Markdown | No structure issues |

## Related Standards

- [suppression.md](suppression.md) - How to suppress findings
- [pm-plugin-development:plugin-architecture](../../plugin-architecture/SKILL.md) - Plugin quality standards
