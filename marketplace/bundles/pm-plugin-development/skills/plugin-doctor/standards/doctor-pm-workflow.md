# Doctor PM-Workflow Workflow

Follows the common workflow pattern (see SKILL.md). Reference guide: `pm-workflow-guide.md`.

## Trigger

Execute this workflow when:
- Component path matches `marketplace/bundles/pm-workflow/**`
- Frontmatter contains `implements:` pointing to pm-workflow contract

## Parameters

- `component` (optional): Specific component path to validate
- `--no-fix` (optional): Diagnosis only, no fixes

## PM-Workflow Validation Rules

For each component, check against `pm-workflow-guide.md`:

### pm-implicit-script-call (PM-001)

- Scan all bash blocks for `execute-script.py` calls
- Verify all parameters are explicit (no "see API" references)
- Flag if ellipsis or placeholder notation found

### pm-generic-api-reference (PM-002)

- Scan document for phrases like "see * API", "refer to * documentation"
- Flag if found near script call context

### pm-wrong-plan-parameter (PM-003) / pm-missing-plan-parameter (PM-004)

- Extract script name from each `execute-script.py` call
- Check parameter against matrix in pm-workflow-guide.md
- Flag PM-003 if wrong parameter used
- Flag PM-004 if required plan parameter missing

### pm-invalid-contract-path (PM-005) / pm-contract-non-compliance (PM-006)

- Extract contract path from frontmatter
- Verify contract file exists (PM-005 if not)
- Load contract and check compliance (PM-006 if non-compliant)

## PM-Workflow Fix Categories

**Safe fixes** (auto-apply unless --no-fix):
- PM-003: Swap `--plan-id` ↔ `--trace-plan-id`
- PM-004: Add missing plan parameter

**Risky fixes** (require confirmation):
- PM-001: Add explicit parameters (requires script documentation lookup)
- PM-002: Replace generic reference with explicit call
- PM-005: Correct contract path or remove `implements:`
- PM-006: Add missing contract requirements
