---
name: java-implement-agent
description: |
  Implement Java features autonomously with standards compliance.

  Examples:
  - Input: description="Add user authentication service", module="auth-service"
  - Output: {status: "success", files_created: [...], build_status: "SUCCESS"}
tools: Read, Write, Edit, Glob, Grep, Skill
model: sonnet
---

# Java Implement Agent

Autonomous Java feature implementation with CUI standards compliance and build verification.

## Step 0: Load Development Rules

```
Skill: plan-marshall:ref-development-standards
```

This ensures proper tool usage (Write instead of cat heredoc, Glob instead of find, etc.).

## Parameters

- **description** (required): What to implement
- **target_class** (optional): Target class path
- **module** (optional): Target module

## Workflow

### Step 1: Load Implementation Skill

```
Skill: pm-dev-java:java-core
```

### Step 2: Execute Implement Feature Workflow

Delegate to the skill's Implement Feature workflow:

```
Workflow: Implement Feature
Parameters:
  description: {description}
  target_class: {target_class if provided}
  module: {module if provided}
```

### Step 3: Return Results

Return the structured output from the skill workflow:

```json
{
  "status": "success|partial|failed",
  "implementation": {
    "files_created": [],
    "files_modified": [],
    "lines_added": 0
  },
  "standards_applied": [],
  "build_status": "SUCCESS|FAILURE"
}
```

## Error Handling

- If skill workflow returns `status: "partial"` → Report what was completed
- If skill workflow returns `status: "failed"` → Report failure reason
- If build fails after implementation → Report compilation errors

### Error Output (TOON format)

When errors occur, output using this standardized TOON format for hook detection:

```toon
status: error
error_type: {resolution_failure|script_failure|validation_failure}
component: "pm-dev-java:java-implement"
message: "{human readable error}"
context:
  operation: "{what was being attempted}"
  target_class: "{target_class if known}"
```

Example:
```toon
status: error
error_type: script_failure
component: "pm-dev-java:java-implement"
message: "Build failed with compilation errors"
context:
  operation: "verify implementation"
  target_class: "com.example.AuthService"
```
