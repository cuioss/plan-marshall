# Deliverables Format

This document covers deliverable headings, references, and title guidelines.

**Full Structure**: See `pm-workflow:manage-solution-outline/standards/deliverable-contract.md` for the complete deliverable structure including Metadata, Profiles, and Verification fields.

## Terminology

**Why "Deliverables" not "Goals"?**

Solution outlines contain concrete work items, not abstract goals:
- A goal is an outcome: "Users can authenticate via JWT"
- A deliverable is work product: "Create JwtValidationService class"

Deliverables describe what will be built, not why.

## Deliverable Headings

Each deliverable uses a level-3 heading with sequential number:

```markdown
## Deliverables

### 1. Create JwtValidationService class

### 2. Add configuration support

### 3. Implement unit tests
```

**Format**: `### N. Title`

**Rules**:
- `N` is a positive integer starting from 1
- Numbers must be sequential (1, 2, 3, ...)
- Title is a concrete action phrase
- Title should be unique within document

## Title Guidelines

**Good Titles** (concrete, actionable):
- "Create JwtValidationService class"
- "Extract TokenService from AuthenticationService"
- "Add unit tests for session timeout"
- "Update API documentation for v2 endpoints"

**Bad Titles** (vague, abstract):
- "Implement authentication" (too broad)
- "Fix the bug" (not specific)
- "Make it work" (not actionable)
- "Goal 1" (not descriptive)

## Reference Format

When tasks reference deliverables, use the full reference:

```toon
deliverable: "1. Create JwtValidationService class"
```

**Format**: `N. Title` (number, dot, space, title)

**Why full reference?**
- Self-documenting: task shows what it implements
- Stable: survives reordering in solution
- Searchable: can grep for deliverable title
- Human-readable in task listings

## Parsing Deliverable References

The `manage-solution-outline` script provides functions for parsing and extracting deliverables.

See: `pm-workflow:manage-solution-outline:manage-solution-outline`

**Key functions in script**:
- `validate_deliverable(str) -> (int, str)` - Parse `N. Title` format, return (number, full_reference)
- `extract_deliverables(section) -> list[dict]` - Extract from `### N. Title` headings

## Task Integration

When creating tasks that implement deliverables, use heredoc:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: Implement JWT validation service
deliverables: [1]
domain: java
steps:
  - Create interface
  - Implement validation
  - Add tests
EOF
```

**Note**: `deliverables` accepts the numeric part(s) as an array. The task stores the full reference internally.

## Listing Deliverables

To extract deliverables from a solution document:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  list-deliverables \
  --plan-id {plan_id}
```

**Output**:
```toon
status: success
plan_id: my-feature
deliverable_count: 4

deliverables[4]:
- number: 1
  title: Create JwtValidationService class
  reference: 1. Create JwtValidationService class
- number: 2
  title: Add configuration support
  reference: 2. Add configuration support
- number: 3
  title: Implement unit tests
  reference: 3. Implement unit tests
- number: 4
  title: Add JavaDoc documentation
  reference: 4. Add JavaDoc documentation
```

## Ordering and Dependencies

Deliverable numbers indicate **suggested execution order**, not strict dependencies.

**When order matters**: Document in the Approach section:

```markdown
## Approach

1. Start with deliverable 1 (interface definition)
2. Deliverables 2-3 can proceed in parallel
3. Deliverable 4 depends on 1-3 completion
```

**When order doesn't matter**: Keep deliverables logically grouped but note flexibility:

```markdown
## Approach

Deliverables 1-3 can be implemented in any order. Deliverable 4 (documentation) should follow implementation.
```
