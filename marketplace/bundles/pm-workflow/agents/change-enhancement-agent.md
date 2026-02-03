---
name: change-enhancement-agent
description: Generic enhancement workflow for improving existing functionality
tools: Read, Glob, Grep, Bash, AskUserQuestion, Skill
model: sonnet
skills: plan-marshall:ref-development-standards
---

# Change Enhancement Agent

Generic agent for `enhancement` change type. Handles requests to improve or extend existing functionality across all domains.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## When Used

This agent handles requests with `change_type: enhancement`:
- "Improve error messages"
- "Add validation to the form"
- "Extend search to support filters"
- "Optimize the query performance"

## Step 0: Load Skills (MANDATORY)

```
Skill: plan-marshall:ref-development-standards
```

## Workflow

### Step 0.5: Log Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-workflow:change-enhancement-agent) Starting"
```

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

### Step 2: Identify Affected Components

Use Glob/Grep to find components that need enhancement:

1. **Primary targets** - Files directly mentioned in request
2. **Related components** - Files that interact with primary targets
3. **Test files** - Tests that cover affected functionality

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:change-enhancement-agent) Affected: {N} files in {modules}"
```

### Step 3: Assess Impact

For each affected file:

1. **Change scope** - How much of the file changes?
2. **Interface changes** - Do signatures/APIs change?
3. **Test impact** - Do tests need updates?

### Step 4: Build Enhancement Deliverables

For each enhancement:

```markdown
### {N}. Enhance {Component Type}: {Name}

**Metadata:**
- change_type: enhancement
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {previous deliverable if sequential}

**Profiles:**
- implementation

**Affected files:**
- `{path/to/existing/file1}`
- `{path/to/existing/file2}`

**Change per file:**
- `{file1}`: {specific changes to make}
- `{file2}`: {specific changes to make}

**Verification:**
- Command: {build/test command}
- Criteria: {success criteria}

**Success Criteria:**
- Enhancement is implemented
- Existing functionality preserved
- Tests pass
```

### Step 5: Add Test Update Deliverable (if needed)

```markdown
### {N+1}. Update Tests: {Enhanced Feature}

**Metadata:**
- change_type: enhancement
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {implementation deliverable}

**Profiles:**
- module_testing

**Affected files:**
- `{path/to/test/file}`

**Change per file:**
- `{test_file}`: Update tests for {enhanced functionality}

**Verification:**
- Command: {test command}
- Criteria: Tests pass, coverage maintained

**Success Criteria:**
- Tests cover new behavior
- Existing tests still pass
```

### Step 6: Write Solution Outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
# Solution: {Enhancement Title}

plan_id: {plan_id}

## Summary

{2-3 sentence summary of the enhancement}

## Deliverables

{deliverables from Steps 4-5}
EOF
```

### Step 7: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:change-enhancement-agent) Complete: {N} deliverables (enhancement)"
```

## Output

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: enhancement
```

## CONSTRAINTS

### MUST NOT
- Use Read tool for `.plan/` files
- Create new files (enhancement = modify existing)
- Break existing functionality

### MUST DO
- Access `.plan/` files ONLY via execute-script.py
- Preserve existing behavior while enhancing
- Update tests when behavior changes
- Return structured TOON output
