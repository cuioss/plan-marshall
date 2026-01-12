# Requirements Severity Guidelines

Decision criteria for handling requirements findings based on severity, type, and context.

## Severity-to-Action Mapping

| Severity | Default Action | Override Conditions |
|----------|----------------|---------------------|
| **Structure Error** | Fix (mandatory) | None - requirements must be parseable |
| **Missing Traceability** | Fix (mandatory) | Document exception for meta-requirements |
| **Format Issue** | Fix preferred | Accept in legacy imports with migration plan |
| **Style Warning** | Consider | Accept if consistent within document |

## Decision by Finding Type

### Structure Issues

| Type | Action | Justification |
|------|--------|---------------|
| Invalid requirement ID | Fix | Breaks references |
| Missing acceptance criteria | Fix | Requirements must be testable |
| Broken cross-reference | Fix | Documentation integrity |
| Malformed AsciiDoc | Fix | Rendering failures |

### Traceability Issues

| Type | Action | Notes |
|------|--------|-------|
| No implementation reference | Fix | Core requirement value |
| No test reference | Fix | Verification requirement |
| Orphaned implementation | Fix | Dead code indicator |
| Meta-requirement (no impl) | Accept | Document as exception |

### Format Issues

| Type | Action | Context |
|------|--------|---------|
| Non-standard heading | Fix | Consistency |
| Missing metadata | Fix | Required fields |
| Inconsistent ID format | Fix | Convention compliance |
| Style deviation | Accept | Low impact |

## Context Modifiers

### New Requirements vs Imported

| Context | Guidance |
|---------|----------|
| **New requirements** | Hold to full standard - fix all issues |
| **Imported requirements** | More lenient - suppress with migration plan |
| **Active revision** | Fix issues encountered during editing |

### Draft vs Approved

| Context | Guidance |
|---------|----------|
| **Draft requirements** | Some incompleteness acceptable |
| **Approved requirements** | Full compliance required |
| **Deprecated requirements** | Accept existing issues |

## Acceptable to Accept

### Always Acceptable

| Finding Type | Reason |
|--------------|--------|
| Draft placeholders | Work in progress |
| Meta-requirements (no impl) | By definition non-implementable |
| External reference format | Cannot control external systems |
| Historical imports | Tracked for migration |

### Conditionally Acceptable

| Finding Type | Condition |
|--------------|-----------|
| Format deviations | In imported requirements with migration plan |
| Style warnings | When consistent within document section |
| Minor cross-ref issues | When document is being restructured |

### Never Acceptable

| Finding Type | Reason |
|--------------|--------|
| Duplicate requirement IDs | Breaks traceability |
| Missing acceptance criteria | Requirements must be testable |
| Broken internal references | Document corruption |
| Unparseable AsciiDoc | Rendering failure |

## Iteration Limits

During finalize phase:

| Iteration | Focus |
|-----------|-------|
| 1 | Fix all structure errors |
| 2 | Fix traceability issues |
| 3 | Review format issues, accept or fix |
| MAX (5) | Accept remaining, document for future |

## Quick Decision Flowchart

```
Is it a structure error?
  -> Yes -> FIX (no exceptions)

Is it missing traceability?
  -> Yes, functional requirement -> FIX
  -> Yes, meta-requirement -> ACCEPT (document exception)

Is it a format issue in new content?
  -> Yes -> FIX

Is it a format issue in imported content?
  -> Yes, with migration plan -> ACCEPT
  -> No migration plan -> Create plan, then ACCEPT

Is it a style warning?
  -> Yes -> ACCEPT (unless egregious)
```

## Related Standards

- [suppression.md](suppression.md) - How to suppress findings
- [pm-requirements:requirements-authoring](../../requirements-authoring/SKILL.md) - Authoring standards
