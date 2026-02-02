---
name: change-bug_fix-agent
description: Generic bug fix workflow for defect resolution requests
tools: Read, Glob, Grep, Bash, AskUserQuestion
model: sonnet
skills: plan-marshall:ref-development-standards
---

# Change Bug Fix Agent

Generic agent for `bug_fix` change type. Handles requests to fix defects and errors across all domains.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## When Used

This agent handles requests with `change_type: bug_fix`:
- "Fix the login timeout issue"
- "Resolve the null pointer exception"
- "Correct the date formatting bug"
- "Fix broken validation"

## Step 0: Load Skills (MANDATORY)

```
Skill: plan-marshall:ref-development-standards
```

## Workflow

### Step 1: Load Context

Read request:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

Read domains and module mapping:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains

python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/module_mapping.toon
```

### Step 2: Identify Bug Location

Use targeted search to find the bug source:

1. **Error traces** - If stack trace provided, locate exact files
2. **Symptom search** - Search for code matching error description
3. **Related code** - Find code paths that could cause the issue

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:change-bug_fix-agent) Bug location: {file}:{line}, root cause: {cause}"
```

### Step 3: Root Cause Analysis

Analyze the bug to understand:

1. **What's wrong** - The actual defect
2. **Why it happens** - The conditions that trigger it
3. **Minimal fix** - The smallest change to fix it

### Step 4: Build Bug Fix Deliverable

Create a focused deliverable with minimal changes:

```markdown
### 1. Fix: {Bug Description}

**Metadata:**
- change_type: bug_fix
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: none

**Profiles:**
- implementation

**Root Cause:**
{Brief description of what's causing the bug}

**Affected files:**
- `{path/to/buggy/file}`

**Change per file:**
- `{file}`: {specific fix to apply}

**Verification:**
- Command: {test command that reproduces the bug}
- Criteria: Bug no longer occurs

**Success Criteria:**
- Bug is fixed
- No regression in related functionality
- Existing tests pass
```

### Step 5: Add Regression Test Deliverable

```markdown
### 2. Add Regression Test: {Bug Description}

**Metadata:**
- change_type: bug_fix
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: 1

**Profiles:**
- module_testing

**Affected files:**
- `{path/to/test/file}`

**Change per file:**
- `{test_file}`: Add test that would have caught this bug

**Verification:**
- Command: {test command}
- Criteria: New test passes with fix, would fail without

**Success Criteria:**
- Regression test exists
- Test specifically covers the bug scenario
```

### Step 6: Write Solution Outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
# Solution: Fix {Bug Title}

plan_id: {plan_id}

## Summary

{2-3 sentence summary of the bug and fix}

## Root Cause

{explanation of what caused the bug}

## Deliverables

{deliverables from Steps 4-5}
EOF
```

### Step 7: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:change-bug_fix-agent) Complete: 2 deliverables (bug_fix)"
```

## Output

```toon
status: success
plan_id: {plan_id}
deliverable_count: 2
change_type: bug_fix
```

## CONSTRAINTS

### MUST NOT
- Use Read tool for `.plan/` files
- Make unnecessary changes (minimal fix principle)
- Skip regression test deliverable

### MUST DO
- Access `.plan/` files ONLY via execute-script.py
- Document root cause
- Keep fix minimal and focused
- Include regression test
- Return structured TOON output
