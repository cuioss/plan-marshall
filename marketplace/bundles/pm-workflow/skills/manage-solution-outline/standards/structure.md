# Solution Outline Structure

This document defines the required structure for `solution_outline.md` documents.

## File Location

```
.plan/plans/{plan_id}/solution_outline.md
```

## Required Sections

### Header

```markdown
# Solution: {title}

plan_id: {plan_id}
created: {timestamp}
```

- Title should summarize the solution (not just repeat request title)
- `plan_id` must match directory name
- Timestamp in ISO 8601 format

### Summary (Required)

```markdown
## Summary

{2-3 sentences describing the approach}
```

**Content Guidelines**:
- What will be built/changed
- Why this approach was chosen
- Expected outcome

**Bad Example**: "Implement the requested feature" (too vague)

**Good Example**: "Implement a JWT token validation service for the authentication module. The service will validate tokens, extract claims, and integrate with the existing security context."

### Overview (Required)

```markdown
## Overview

```
{ASCII diagram}
```
```

**Requirements**:
- Must contain ASCII diagram
- Diagram shows architecture, components, or flow
- Use box-drawing characters for clarity
- Label new vs existing components

See [diagrams.md](diagrams.md) for diagram patterns.

### Deliverables (Required)

```markdown
## Deliverables

### 1. {First deliverable title}

{Description}

### 2. {Second deliverable title}

{Description}
```

**Requirements**:
- Uses `###` headings (level 3)
- Sequential numbering starting from 1
- Each deliverable independently achievable
- Concrete titles (not abstract goals)

See [deliverables.md](deliverables.md) for format details.

## Optional Sections

### Approach

```markdown
## Approach

{Execution strategy and order}
```

**When to Include**:
- Complex multi-step implementations
- Specific order matters
- Dependencies between deliverables

### Dependencies

```markdown
## Dependencies

{External requirements, libraries, services}
```

**When to Include**:
- New dependencies needed
- External service requirements
- Environment prerequisites

### Risks and Mitigations

```markdown
## Risks and Mitigations

- **Risk**: {description}
  - **Mitigation**: {how to address}
```

**When to Include**:
- Significant technical risks
- Breaking changes
- Performance concerns

## Validation

The `manage-plan-document solution validate` command checks:

1. Document exists at expected location
2. Required sections present: Summary, Overview, Deliverables
3. Deliverables section has numbered `### N. Title` items
4. At least one deliverable defined

**Validation Command**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  solution validate \
  --plan-id {plan_id}
```

**Success Output**:
```toon
status: success
plan_id: my-feature
document: solution
file: solution_outline.md

validation:
  sections_found: summary,overview,deliverables,approach,dependencies,risks
  deliverable_count: 4
  deliverables[4]:
  - 1. Create JwtValidationService class
  - 2. Add configuration properties
  - 3. Implement unit tests
  - 4. Add JavaDoc documentation
```

**Failure Output**:
```toon
status: error
plan_id: my-feature
document: solution
error: validation_failed

issues[2]:
- Missing required section: Overview
- No numbered deliverables found in Deliverables section
```

## Section Order

Sections should appear in this order:

1. Header (# Solution: {title})
2. Metadata (plan_id, created)
3. Summary
4. Overview
5. Deliverables
6. Approach (if present)
7. Dependencies (if present)
8. Risks and Mitigations (if present)
