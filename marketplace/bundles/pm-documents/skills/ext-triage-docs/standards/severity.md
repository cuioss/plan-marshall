# Documentation Severity Guidelines

Decision criteria for handling documentation findings based on severity, type, and context.

## Severity-to-Action Mapping

| Severity | Default Action | Override Conditions |
|----------|----------------|---------------------|
| **Broken Link** | Fix (mandatory) | None - links must work |
| **Invalid Xref** | Fix (mandatory) | None - references must resolve |
| **Format Error** | Fix preferred | Accept in legacy with migration plan |
| **Style Warning** | Consider | Accept if document is stable |

## Decision by Finding Type

### Link Issues

| Type | Action | Justification |
|------|--------|---------------|
| Broken internal link | Fix | Document integrity |
| Broken external link | Fix or remove | User experience |
| Deprecated URL | Update | Maintainability |
| Insecure HTTP link | Upgrade to HTTPS | Security |

### Cross-Reference Issues

| Type | Action | Notes |
|------|--------|-------|
| Invalid xref target | Fix | Must resolve |
| Missing anchor | Create anchor | Enable reference |
| Duplicate anchor ID | Rename one | Avoid ambiguity |
| Orphaned anchor | Remove or use | Cleanup |

### AsciiDoc Format Issues

| Type | Action | Context |
|------|--------|---------|
| Malformed syntax | Fix | Rendering failure |
| Invalid attribute | Fix | Functionality |
| Heading hierarchy | Fix | Structure |
| List formatting | Fix or accept | Style |

### ADR Issues

| Type | Action | Context |
|------|--------|---------|
| Missing required section | Fix | Standard compliance |
| Invalid status value | Fix | Tracking |
| Missing date | Add | History |
| Outdated format | Migrate or accept | Legacy |

## Context Modifiers

### Active vs Archived

| Context | Guidance |
|---------|----------|
| **Active documentation** | Fix all issues |
| **Archived/Historical** | Accept format issues, fix broken links |
| **Draft documentation** | Some incompleteness acceptable |

### Generated vs Authored

| Context | Guidance |
|---------|----------|
| **Authored content** | Full compliance required |
| **Generated content** | Fix generator, not output |
| **Imported content** | Migrate or accept with plan |

## Acceptable to Accept

### Always Acceptable

| Finding Type | Reason |
|--------------|--------|
| Style preferences | Non-functional |
| External link variations | Cannot control |
| Historical ADR format | Captured as-is |
| Generated doc quirks | Fix generator instead |

### Conditionally Acceptable

| Finding Type | Condition |
|--------------|-----------|
| Format deviations | In imported docs with migration plan |
| Missing sections | In draft documents |
| Link warnings | External sites with known issues |

### Never Acceptable

| Finding Type | Reason |
|--------------|--------|
| Broken internal links | Document corruption |
| Invalid xref targets | Navigation failure |
| Unparseable content | Rendering failure |
| Duplicate IDs | Ambiguous references |

## Iteration Limits

During finalize phase:

| Iteration | Focus |
|-----------|-------|
| 1 | Fix all broken links and xrefs |
| 2 | Fix format errors |
| 3 | Review style warnings, accept or fix |
| MAX (5) | Accept remaining, document for future |

## Quick Decision Flowchart

```
Is it a broken link or invalid xref?
  -> Yes -> FIX (no exceptions)

Is it a format error in active docs?
  -> Yes -> FIX

Is it a format error in archived docs?
  -> Yes -> ACCEPT (document age exception)

Is it a style warning?
  -> In active, visible doc -> Consider fixing
  -> In archived/internal doc -> ACCEPT

Is it in generated content?
  -> Yes -> Fix generator or ACCEPT
```

## ADR-Specific Guidelines

### Status Transitions

| Current Status | Valid Actions |
|----------------|---------------|
| Proposed | Accept, Supersede, Reject |
| Accepted | Supersede, Deprecate |
| Superseded | None (final) |
| Deprecated | None (final) |
| Rejected | None (final) |

### Required Sections

Every ADR must have:
- Title with ADR number
- Status
- Context
- Decision
- Consequences

Missing sections = **Fix** (no exceptions)

## Related Standards

- [suppression.md](suppression.md) - How to suppress findings
- [pm-documents:cui-documentation](../../cui-documentation/SKILL.md) - Documentation standards
