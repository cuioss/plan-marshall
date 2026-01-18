# Semantic Verification Criteria

## Overview

Brief description of what this test case verifies.

## Scope Correctness

The workflow must analyze the correct scope:

- [ ] All component types mentioned in request are analyzed
- [ ] Scope boundaries are correctly determined
- [ ] Explicit scope decisions are logged with `[DECISION]` tag

**Expected scope**: {Describe the expected scope}

## Completeness

All expected items must be found:

- [ ] All affected files from golden reference are identified
- [ ] No false negatives (missing items)
- [ ] Count matches expected range

**Expected count**: {N} affected files (see golden reference)

## Decision Quality

Decisions must have clear rationale:

- [ ] Exclusion decisions are explicitly documented
- [ ] Rationale explains the "why" not just the "what"
- [ ] Decision trail is traceable in work log

**Expected decisions**:
- {Describe expected key decisions}

## Scoring Guidance

**90-100 (Excellent)**: All criteria met, decisions well-documented
**70-89 (Good)**: Most criteria met, minor documentation gaps
**50-69 (Partial)**: Significant gaps, but core items present
**0-49 (Poor)**: Major failures, key items missing
