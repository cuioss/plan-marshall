---
name: ext-triage-plugin
description: Triage extension for marketplace plugin findings during plan-finalize phase
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-triage
---

# Plugin Development Triage Extension

Provides decision-making knowledge for triaging marketplace plugin development findings during the finalize phase.

## Purpose

This skill is a **triage extension** loaded by the plan-finalize workflow skill when processing plugin development findings (Python scripts, markdown documentation, YAML configurations).

**Key Principle**: This skill provides **knowledge**, not workflow control. The finalize skill owns the process.

## When This Skill is Loaded

Loaded via `resolve-workflow-skill-extension --domain plan-marshall-plugin-dev --type triage` during finalize phase when:

1. Python script tests fail (pytest)
2. Plugin-doctor reports issues
3. Markdown linting issues detected
4. YAML validation errors occur

## Standards

| Document | Purpose |
|----------|---------|
| [suppression.md](standards/suppression.md) | Python and markdown suppression syntax |
| [severity.md](standards/severity.md) | Plugin-specific severity guidelines |

## Extension Registration

Registered in marshal.json under the plugin development domain:

```json
"plan-marshall-plugin-dev": {
  "workflow_skill_extensions": {
    "triage": "pm-plugin-development:ext-triage-plugin"
  }
}
```

## Quick Reference

### Suppression Methods

| Finding Type | Syntax |
|--------------|--------|
| Python linting | `# noqa: E501` or `# noqa` |
| Python typing | `# type: ignore` |
| Pytest skip | `@pytest.mark.skip(reason="...")` |
| Markdown lint | `<!-- markdownlint-disable MD001 -->` |
| YAML validation | Configure `.yamllint` rules |
| Plugin-doctor | Fix structurally (no suppression) |

### Decision Guidelines

| Severity | Default Action |
|----------|----------------|
| Test failure | **Fix** (tests must pass) |
| Plugin-doctor error | **Fix** (quality gate) |
| Script type error | Fix or add type ignore |
| Documentation issue | Fix for consistency |
| Frontmatter warning | **Fix** (required for loading) |

### Common False Positives

These findings frequently appear in plugin development but are typically acceptable:

| Finding | Context | Why It's a False Positive |
|---------|---------|--------------------------|
| MD041 (first line heading) | SKILL.md, agent.md, command.md | YAML frontmatter precedes the first heading |
| MD013 (line length) | Tables in standards/*.md | Tables with multiple columns cannot be wrapped |
| MD033 (inline HTML) | HTML comments for markdownlint control | `<!-- markdownlint-disable -->` is intentional |
| E501 (line too long) | Script help text, URL strings | Long help strings and URLs are not splittable |
| F401 (unused import) | `__init__.py` re-exports | Imports for public API re-export |
| Type ignore on `json.loads` | Dynamic JSON parsing in scripts | Return type depends on input, not statically known |
| Plugin-doctor Rule 8 | Bootstrap/init scripts | Bootstrap scripts need absolute paths for initial setup |
| Heading skip (MD001) | Skills with `## Enforcement` after `#` title | Intentional structure per enforcement block pattern |

### YAML Frontmatter Edge Cases

| Issue | Resolution |
|-------|-----------|
| `tools:` as comma-separated string | Correct format — not YAML array syntax |
| `description:` with pipe or colon | Wrap in quotes: `description: "Analyze: find issues"` |
| `user-invocable:` as string | Must be boolean: `true` or `false`, not `"true"` |
| Multi-line description | Use `>-` folded scalar or single-line |

### Acceptable to Accept

- Markdown formatting inside code blocks and examples
- Test skip for environment-specific tests (with reason)
- Type ignores for dynamic patterns (with explanation comment)
- Plugin-doctor warnings in experimental code
- MD013 in wide tables (>4 columns)
- Pytest xfail with tracked issue reference

### Never Accept

- Test failures without skip/xfail annotation
- Plugin-doctor critical issues (component will not load)
- Import errors in scripts (will not execute)
- YAML syntax errors in frontmatter (component invisible to marketplace)
- Missing `name` or `description` in frontmatter

## Related Documents


- `pm-plugin-development:plugin-architecture` - Plugin patterns
