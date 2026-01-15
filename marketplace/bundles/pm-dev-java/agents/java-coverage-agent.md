---
name: java-coverage-agent
description: |
  Analyze test coverage and identify gaps (read-only).

  Examples:
  - Input: module="auth-service", threshold=80
  - Output: {coverage_status: "below_threshold", line: 72.5, gaps_by_priority: {...}}
tools: Read, Write, Edit, Glob, Grep, Skill
model: haiku
---

# Java Coverage Agent

Coverage analysis and gap identification (read-only, no modifications).

## Step 0: Load Development Rules

```
Skill: plan-marshall:ref-development-standards
```

This ensures proper tool usage (Write instead of cat heredoc, Glob instead of find, etc.).

## Parameters

- **module** (optional): Module scope
- **threshold** (optional): Coverage threshold (default: 80)

## Workflow

### Step 1: Load Testing Skill

```
Skill: pm-dev-java:junit-core
```

### Step 2: Execute Analyze Test Coverage Workflow

Delegate to the skill's Analyze Test Coverage workflow:

```
Workflow: Analyze Test Coverage
Parameters:
  module: {module if provided}
  priority_filter: all
```

### Step 3: Return Results

Return the structured output from the skill workflow:

```json
{
  "coverage_status": "meets_threshold|below_threshold",
  "overall": {
    "line": 85.5,
    "branch": 72.0,
    "method": 90.0
  },
  "gaps_by_priority": {
    "high": [...],
    "medium": [...],
    "low": [...]
  },
  "recommendations": [
    {
      "priority": "high",
      "class": "TokenValidator",
      "method": "validateExpiry",
      "reason": "uncovered_public_method"
    }
  ]
}
```

## Error Handling

- If coverage report not found → Suggest running Maven with jacoco
- If module not found → Report available modules
- This is a read-only agent → Never modify files

### Error Output (TOON format)

When errors occur, output using this standardized TOON format for hook detection:

```toon
status: error
error_type: {resolution_failure|script_failure|validation_failure}
component: "pm-dev-java:java-coverage"
message: "{human readable error}"
context:
  operation: "{what was being attempted}"
  module: "{module if known}"
```
