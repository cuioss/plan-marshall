# Criteria Format Standard

This document defines how to write semantic verification criteria for LLM-as-judge assessment.

## Purpose

Criteria files provide natural language instructions for the LLM to evaluate workflow outputs. Unlike structural checks (which are deterministic), semantic criteria assess qualities that require understanding context and intent.

## Criteria Types

### 1. Scope Criteria

Evaluate whether the workflow analyzed the correct scope.

**Questions to address:**
- Did it analyze all component types mentioned in the request?
- Did it correctly determine scope boundaries?
- Did it explicitly document scope decisions?

**Example:**
```markdown
## Scope Correctness

The workflow must analyze the correct scope:

1. **Component Types**: Request mentions "agents, commands, and skills" - all three types must be analyzed
2. **Bundle Scope**: Request doesn't specify bundles - should scan all bundles
3. **Decision Logging**: Scope decisions must be logged to `decision.log`
```

### 2. Completeness Criteria

Evaluate whether all expected items were found.

**Questions to address:**
- Are all affected files identified?
- Are there missing items (false negatives)?
- Does the count match expectations?

**Example:**
```markdown
## Completeness

All expected items must be found:

1. **File Coverage**: All files with JSON output specifications must be found
2. **No Omissions**: Cross-check against golden reference - no files should be missing
3. **Count Validation**: Expected ~10-12 affected files (per golden reference)
```

### 3. Decision Quality Criteria

Evaluate the quality of decisions and their rationale.

**Questions to address:**
- Are exclusion decisions documented?
- Does rationale explain the "why"?
- Is the decision trail traceable?

**Example:**
```markdown
## Decision Quality

Decisions must have clear rationale:

1. **Exclusion Documentation**: If items are excluded, `decision.log` must contain an explanation
2. **Rationale Depth**: Must explain reasoning, not just state the decision
3. **Traceability**: Each decision should reference the source analysis
```

## Writing Effective Criteria

### Be Specific

| Vague | Specific |
|-------|----------|
| "Output should be complete" | "All 11 affected files from golden reference must appear in affected_files list" |
| "Decisions should be good" | "Exclusion decisions must include both what was excluded and why" |
| "Scope should be correct" | "Must analyze agents, commands, and skills across all bundles" |

### Use Checklists

Format criteria as checklists when possible:

```markdown
- [ ] Scope includes all three component types
- [ ] Affected files count is within expected range (10-12)
- [ ] Skills exclusion decision is documented with rationale
```

### Reference Golden Output

Connect criteria to specific expectations:

```markdown
## Expected Affected Files

The following files must be identified (from golden reference):
- marketplace/bundles/pm-dev-java/agents/java-implement-agent.md
- marketplace/bundles/pm-dev-java/agents/java-implement-tests-agent.md
...

Missing any of these indicates a completeness failure.
```

### Define Scoring Anchors

Provide guidance for scoring:

```markdown
## Scoring Guidance

**90-100 (Excellent)**: All criteria met, decisions well-documented
**70-89 (Good)**: Most criteria met, minor documentation gaps
**50-69 (Partial)**: Significant gaps, but core items present
**0-49 (Poor)**: Major failures, key items missing
```

## Template Structure

```markdown
# Semantic Verification Criteria

## Overview

Brief description of what this test case verifies.

## Scope Correctness

{Scope criteria with specific expectations}

## Completeness

{Completeness criteria with specific expectations}

## Decision Quality

{Decision quality criteria with specific expectations}

## Scoring Guidance

{Scoring anchors for LLM-as-judge}
```

## Integration with LLM-as-Judge

When performing assessment, the LLM will:

1. Read these criteria files
2. Read the actual workflow output
3. Read the golden reference
4. Score each dimension (0-100)
5. Explain reasoning for each score
6. Identify specific gaps or errors

The criteria format directly impacts assessment quality - clear, specific criteria yield more accurate assessments.
