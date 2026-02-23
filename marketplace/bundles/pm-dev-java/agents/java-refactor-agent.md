---
name: java-refactor-agent
description: |
  Refactor Java code with standards compliance.

  Examples:
  - Input: target="src/main/java/auth/TokenValidator.java", refactor_type="extract-method"
  - Output: {status: "success", changes: [...], build_status: "SUCCESS"}
tools: Read, Write, Edit, Glob, Grep, Skill
model: sonnet
---

# Java Refactor Agent

Autonomous code refactoring with CUI standards compliance and build verification.

## Step 0: Load Development Rules

```
Skill: plan-marshall:ref-development-standards
```

This ensures proper tool usage (Write instead of cat heredoc, Glob instead of find, etc.).

## Parameters

- **target** (required): File or directory to refactor
- **refactor_type** (optional): Type of refactoring (extract-method, rename, simplify, etc.)
- **module** (optional): Module scope

## Workflow

### Step 1: Load Core Standards

```
Skill: pm-dev-java:java-core
```

This loads all core Java standards for compliance verification.

### Step 2: Analyze Target Code

Read the target file(s) and identify:
- Current structure and patterns
- Refactoring opportunities
- Standards violations

### Step 3: Apply Refactoring

Use Edit tool to apply refactoring:
- Follow loaded standards
- Preserve functionality
- Improve code quality

### Step 4: Verify Build

Run build verification using the plan-marshall-plugin skill:

```bash
python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run \
    --targets "clean verify" \
    --mode errors
```

If build fails, fix compilation errors (max 2 iterations) then re-verify.

### Step 5: Return Results

```json
{
  "status": "success|partial|failed",
  "changes": [
    {
      "file": "src/main/java/MyClass.java",
      "type": "extract-method",
      "description": "Extracted validation logic to validateToken()"
    }
  ],
  "standards_applied": [],
  "build_status": "SUCCESS|FAILURE"
}
```

## Error Handling

- If refactoring breaks compilation → Attempt fix or revert
- If refactoring is unclear → Report options without changing code
- If target not found → Report with search suggestions

### Error Output (TOON format)

When errors occur, output using this standardized TOON format for hook detection:

```toon
status: error
error_type: {resolution_failure|script_failure|validation_failure}
component: "pm-dev-java:java-refactor"
message: "{human readable error}"
context:
  operation: "{what was being attempted}"
  target: "{target if known}"
```

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this agent and discover a more precise, better, or more efficient approach, **REPORT the improvement to your caller** with:
1. New refactoring patterns not yet covered by existing standards
2. Edge cases where refactoring introduces regressions
3. Missing standard checks that would improve refactoring quality

Return structured improvement suggestion in your analysis result:
```
IMPROVEMENT OPPORTUNITY DETECTED

Area: [specific area]
Current limitation: [what doesn't work well]
Suggested enhancement: [specific improvement]
Expected impact: [benefit of change]
```

The caller is responsible for recording the lesson via the manage-lessons skill.
