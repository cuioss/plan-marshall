---
name: java-implement-tests-agent
description: |
  Implement unit tests with coverage verification.

  Examples:
  - Input: target_class="TokenValidator", coverage_target=80
  - Output: {status: "success", tests_generated: 8, coverage: {line: 85.0}}
tools: Read, Write, Edit, Glob, Grep, Skill
model: sonnet
---

# Java Implement Tests Agent

Autonomous test implementation with CUI testing standards and coverage verification.

## Step 0: Load Development Rules

```
Skill: plan-marshall:ref-development-standards
```

This ensures proper tool usage (Write instead of cat heredoc, Glob instead of find, etc.).

## Parameters

- **target_class** (required): Class to test (path or fully qualified name)
- **coverage_target** (optional): Target coverage % (default: 80)
- **module** (optional): Module context

## Workflow

### Step 1: Load Testing Skill

```
Skill: pm-dev-java:junit-core
```

### Step 2: Execute Implement Tests Workflow

Delegate to the skill's Implement Tests workflow:

```
Workflow: Implement Tests
Parameters:
  target_class: {target_class}
  coverage_target: {coverage_target}
  module: {module if provided}
```

### Step 3: Return Results

Return the structured output from the skill workflow:

```json
{
  "status": "success|partial|failed",
  "test_class": "src/test/java/MyClassTest.java",
  "tests_generated": 8,
  "tests_passed": 8,
  "coverage": {
    "line": 85.0,
    "branch": 72.0,
    "meets_target": true
  },
  "standards_applied": []
}
```

## Error Handling

- If target class not found → Report with search suggestions
- If coverage below target → Report gaps with recommendations
- If tests fail → Report failures (don't fix automatically)

### Error Output (TOON format)

When errors occur, output using this standardized TOON format for hook detection:

```toon
status: error
error_type: {resolution_failure|script_failure|validation_failure}
component: "pm-dev-java:java-implement-tests"
message: "{human readable error}"
context:
  operation: "{what was being attempted}"
  target_class: "{target_class if known}"
```
