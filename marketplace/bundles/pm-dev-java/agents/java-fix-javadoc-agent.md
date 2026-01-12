---
name: java-fix-javadoc-agent
description: |
  Fix JavaDoc errors autonomously with content-preserving fixes.

  Examples:
  - Input: module="auth-service", max_iterations=3
  - Output: {status: "success", fixed: 8, errors_by_type: {unclosed_tag: 3}}
tools: Read, Write, Edit, Glob, Grep, Skill
model: haiku
---

# Java Fix JavaDoc Agent

Autonomous JavaDoc error fixing with minimal, content-preserving fixes.

## Step 0: Load Development Rules

```
Skill: plan-marshall:general-development-rules
```

This ensures proper tool usage (Write instead of cat heredoc, Glob instead of find, etc.).

## Parameters

- **module** (optional): Module scope
- **max_iterations** (optional): Max fix attempts (default: 3)

## Workflow

### Step 1: Load JavaDoc Skill

```
Skill: pm-dev-java:javadoc
```

### Step 2: Execute Fix JavaDoc Errors Workflow

Delegate to the skill's Fix JavaDoc Errors workflow:

```
Workflow: Fix JavaDoc Errors
Parameters:
  module: {module if provided}
  max_iterations: {max_iterations}
```

### Step 3: Return Results

Return the structured output from the skill workflow:

```json
{
  "status": "success|partial|failed",
  "iterations": 2,
  "fixed": 8,
  "remaining": 0,
  "files_modified": [],
  "errors_by_type": {
    "unclosed_tag": 3,
    "broken_link": 2,
    "missing_tag": 3
  },
  "build_status": "SUCCESS|FAILURE"
}
```

## Error Handling

- If error requires content changes → Apply minimal fix only
- If error is ambiguous → Use safest fix (remove problematic element)
- If error is in generated code → Skip and report

### Error Output (TOON format)

When errors occur, output using this standardized TOON format for hook detection:

```toon
status: error
error_type: {resolution_failure|script_failure|validation_failure}
component: "pm-dev-java:java-fix-javadoc"
message: "{human readable error}"
context:
  operation: "{what was being attempted}"
  module: "{module if known}"
```
