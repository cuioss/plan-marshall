# Doctor PM-Workflow Workflow

Validate pm-workflow components and contract compliance.

## Trigger

Execute this workflow when:
- Component path matches `marketplace/bundles/pm-workflow/**`
- Frontmatter contains `implements:` pointing to pm-workflow contract

## Parameters

- `component` (optional): Specific component path to validate
- `--no-fix` (optional): Diagnosis only, no fixes

## Step 1: Load Prerequisites and Standards

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Read references/pm-workflow-guide.md
Read references/fix-catalog.md
```

## Step 2: Discover Components

**If specific component provided**:
- Validate single component

**If pm-workflow bundle**:
```
Glob: pattern="**/*.md", path="marketplace/bundles/pm-workflow"
```

**If contract implementers**:
```
Grep: pattern="^implements:" path="marketplace/bundles"
```

## Step 3: Apply pm-workflow Validation Rules

For each component, check against `pm-workflow-guide.md`:

**Rule 1 - Explicit Script Commands**:
- Scan all bash blocks for `execute-script.py` calls
- Verify all parameters are explicit (no "see API" references)
- Flag PM-001 if ellipsis or placeholder notation found

**Rule 2 - No Generic API Documentation**:
- Scan document for phrases like "see * API", "refer to * documentation"
- Flag PM-002 if found near script call context

**Rule 3 - Correct plan-id vs trace-plan-id**:
- Extract script name from each `execute-script.py` call
- Check parameter against matrix in pm-workflow-guide.md
- Flag PM-003 if wrong parameter used
- Flag PM-004 if required plan parameter missing

**Rule 4 - Contract Implementation** (if `implements:` present):
- Extract contract path from frontmatter
- Verify contract file exists (PM-005 if not)
- Load contract and check compliance (PM-006 if non-compliant)

## Step 4: Categorize and Fix

**Safe fixes** (auto-apply unless --no-fix):
- PM-003: Swap `--plan-id` ↔ `--trace-plan-id`
- PM-004: Add missing plan parameter

**Risky fixes** (require confirmation):
- PM-001: Add explicit parameters (requires script documentation lookup)
- PM-002: Replace generic reference with explicit call
- PM-005: Correct contract path or remove `implements:`
- PM-006: Add missing contract requirements

## Step 5: Verify and Report

```bash
git status --short
```

Display summary with pm-workflow-specific metrics:
- Components validated
- Script calls checked
- Parameter issues found/fixed
- Contract compliance status
