# Scoring Guide

This document provides the rubric for LLM-as-judge scoring of workflow outputs.

## Score Dimensions

Three dimensions are scored independently (0-100 each):

1. **Scope Score**: Did it analyze the correct components?
2. **Completeness Score**: Are all expected items found?
3. **Quality Score**: Are decisions well-reasoned?

The **Overall Score** is the weighted average:
- Scope: 30%
- Completeness: 40%
- Quality: 30%

## Scope Score Rubric

Evaluates whether the workflow analyzed the correct scope.

| Score | Criteria | Examples |
|-------|----------|----------|
| **90-100** | All expected component types analyzed, scope boundaries correct, explicit decisions logged | Request says "agents and commands" - both types scanned, bundles correctly scoped |
| **70-89** | Most components analyzed, minor scope issues | Analyzed agents and commands but missed one bundle |
| **50-69** | Significant scope gaps, missing component types | Analyzed only agents when request included commands |
| **30-49** | Major scope errors | Analyzed wrong component types entirely |
| **0-29** | Wrong scope entirely | Analyzed skills when request was about build configs |

### Key Indicators

**Good Scope:**
- `[DECISION]` log entry explaining scope determination
- All component types from request are represented
- Bundle scope matches request (all vs specific)

**Poor Scope:**
- No scope decision logged
- Missing component types
- Wrong bundles analyzed

## Completeness Score Rubric

Evaluates whether all expected items were found.

| Score | Criteria | Examples |
|-------|----------|----------|
| **90-100** | All expected items found, no false negatives | 11/11 affected files from golden reference found |
| **70-89** | Most items found, 1-2 minor omissions | 10/11 files found, missing one edge case |
| **50-69** | Significant omissions, 3+ missing items | 8/11 files found, pattern of misses |
| **30-49** | Many missing items | Less than half of expected items found |
| **0-29** | Major completeness failure | Most items missing |

### Key Indicators

**Good Completeness:**
- Affected files count matches golden reference
- No items from golden reference are missing
- Edge cases (different bundles, component types) all covered

**Poor Completeness:**
- Missing files from golden reference
- Count significantly below expected
- Pattern of misses (e.g., all commands missed)

## Quality Score Rubric

Evaluates the quality of decisions and rationale.

| Score | Criteria | Examples |
|-------|----------|----------|
| **90-100** | Clear decisions, well-documented rationale, traceable reasoning | "Skills excluded because they document formats, not produce outputs" |
| **70-89** | Good decisions, some rationale gaps | Correct exclusions but rationale is brief |
| **50-69** | Questionable decisions, missing rationale | Items excluded without explanation |
| **30-49** | Poor decisions, contradictory rationale | Exclusions contradict stated criteria |
| **0-29** | No decisions documented, or completely wrong decisions | No `[DECISION]` logs, or wrong inclusions/exclusions |

### Key Indicators

**Good Quality:**
- `[DECISION]` entries explain "why" not just "what"
- Exclusions have specific rationale
- Decision trail is traceable through work log

**Poor Quality:**
- Decisions without rationale
- Inconsistent treatment of similar items
- No decision logging

## Overall Status Determination

| Overall Score | Status |
|---------------|--------|
| **80-100** | PASS |
| **60-79** | WARN (pass with concerns) |
| **0-59** | FAIL |

### PASS Criteria

- Overall score >= 80
- No dimension below 60
- No critical findings

### FAIL Criteria (any of these)

- Overall score < 60
- Any dimension below 40
- Critical finding (missing expected file with no rationale)

## Findings Classification

### Critical (blocks pass)

- Missing expected file with no explanation
- Wrong scope analyzed entirely
- Contradictory decisions

### Error (counts against score)

- Missing expected file with weak explanation
- Incomplete scope analysis
- Missing rationale for decisions

### Warning (noted but doesn't block)

- Minor format issues
- Rationale could be more detailed
- Edge case handling unclear

## Assessment Report Format

```toon
semantic_assessment:
  scope_score: {0-100}
  scope_reasoning: {explanation}
  completeness_score: {0-100}
  completeness_reasoning: {explanation}
  quality_score: {0-100}
  quality_reasoning: {explanation}
  overall_score: {weighted_average}
  overall_status: {pass|warn|fail}
```

## Calibration Notes

- Use golden reference as ground truth
- Don't penalize stylistic differences
- Focus on semantic correctness, not format
- Consider context (complex requests may have acceptable omissions if documented)
