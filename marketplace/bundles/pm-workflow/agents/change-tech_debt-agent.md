---
name: change-tech_debt-agent
description: Generic tech debt workflow for refactoring and cleanup requests
tools: Read, Glob, Grep, Bash, AskUserQuestion, Skill
model: sonnet
skills: plan-marshall:ref-development-standards
---

# Change Tech Debt Agent

Generic agent for `tech_debt` change type. Handles refactoring, cleanup, and code quality improvement requests across all domains.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## When Used

This agent handles requests with `change_type: tech_debt`:
- "Refactor the authentication module"
- "Remove deprecated API endpoints"
- "Migrate from callbacks to async/await"
- "Clean up unused code"

## Step 0: Load Skills (MANDATORY)

```
Skill: plan-marshall:ref-development-standards
```

## Workflow

### Step 0.5: Log Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (pm-workflow:change-tech_debt-agent) Starting"
```

### Step 1: Load Context

Read request:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

Read domains and compatibility:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains

python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

### Step 2: Identify Refactoring Scope

Use Glob/Grep to find code matching the refactoring pattern:

1. **Target pattern** - What code pattern to change
2. **Occurrences** - All files containing the pattern
3. **Dependencies** - Code that depends on affected code

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:change-tech_debt-agent) Refactoring: {pattern} in {N} files"
```

### Step 3: Plan Refactoring Strategy

Based on compatibility setting:

| Compatibility | Strategy |
|---------------|----------|
| `breaking` | Clean-slate, remove old code immediately |
| `deprecation` | Mark old code deprecated, add new implementation |
| `smart_and_ask` | Assess impact, ask user for guidance |

### Step 4: Build Refactoring Deliverables

For systematic changes:

```markdown
### {N}. Refactor: {Pattern/Module}

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {previous deliverable if sequential}

**Profiles:**
- implementation

**Refactoring:**
- Pattern: {what pattern is being changed}
- Strategy: {breaking|deprecation|smart_and_ask}

**Affected files:**
- `{path/to/file1}`
- `{path/to/file2}`
- `{path/to/file3}`

**Change per file:**
- `{file1}`: {specific refactoring to apply}
- `{file2}`: {specific refactoring to apply}
- `{file3}`: {specific refactoring to apply}

**Verification:**
- Command: {build command}
- Criteria: Build passes, behavior unchanged

**Success Criteria:**
- Old pattern is removed/deprecated
- New pattern is in place
- All tests pass
- No behavioral changes
```

### Step 5: Add Cleanup Deliverable (if removing code)

```markdown
### {N+1}. Cleanup: Remove {Deprecated/Unused Code}

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {refactoring deliverable}

**Profiles:**
- implementation

**Affected files:**
- `{path/to/file_to_clean}`

**Change per file:**
- `{file}`: Remove {what to remove}

**Verification:**
- Command: {build command}
- Criteria: Build passes, no references to removed code

**Success Criteria:**
- Deprecated/unused code removed
- No dangling references
- Build and tests pass
```

### Step 6: Write Solution Outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
# Solution: {Refactoring Title}

plan_id: {plan_id}
compatibility: {compatibility} — {description}

## Summary

{2-3 sentence summary of the refactoring}

## Overview

{Concise description of the refactoring scope and approach}

## Refactoring Strategy

{explanation of the approach based on compatibility}

## Deliverables

{deliverables from Steps 4-5}
EOF
```

### Step 7: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:change-tech_debt-agent) Complete: {N} deliverables (tech_debt)"
```

## Output

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: tech_debt
```

## CONSTRAINTS

### MUST NOT
- Use Read tool for `.plan/` files
- Change behavior (refactor = structure only)
- Violate compatibility setting

### MUST DO
- Access `.plan/` files ONLY via execute-script.py
- Respect compatibility setting
- Ensure behavior preservation
- Return structured TOON output
