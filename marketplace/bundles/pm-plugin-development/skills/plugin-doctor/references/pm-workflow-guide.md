# pm-workflow Validation Guide

Reference guide for validating pm-workflow components and skills implementing pm-workflow contracts.

## When to Load

Load this guide when validating:
- Components in `marketplace/bundles/pm-workflow/`
- Components with `implements:` frontmatter pointing to pm-workflow contracts

## pm-implicit-script-call (PM-001): Explicit Script Commands

**Requirement**: All bash script calls must be explicit with all parameters shown.

**Check**:
```
FOR each ```bash block:
  IF contains python3 .plan/execute-script.py:
    VERIFY all parameters are explicit (no "see API" references)
    VERIFY no ellipsis (...) or placeholder notation
```

**Valid**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get \
  --plan-id {plan_id} \
  --number {task_number}
```

**Invalid**:
```bash
# See manage-tasks API for parameters
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get ...
```

**Fix**: Replace generic references with explicit parameter lists.

## pm-generic-api-reference (PM-002): No Generic API Documentation

**Requirement**: Never reference "API documentation" or "see X for details" for script calls.

**Check**:
```
SCAN document for:
  - "see * API"
  - "refer to * documentation"
  - "parameters documented in"
  - "see * for available options"
```

**Fix**: Replace with explicit command examples showing all parameters.

## pm-wrong-plan-parameter (PM-003) / pm-missing-plan-parameter (PM-004): Correct plan-id vs trace-plan-id Usage

**Requirement**: Plan-related components must use correct parameter:
- `--plan-id`: For data operations (read/write plan files, artifacts)
- `--trace-plan-id`: For config lookups and logging context

**Check**:
```
FOR each script call:
  IF script is manage-plan-marshall-config:
    REQUIRE --trace-plan-id (not --plan-id)
  IF script is manage-log:
    REQUIRE --trace-plan-id for context
  IF script is manage-files, manage-tasks, manage-references:
    REQUIRE --plan-id for data operations
```

**Parameter Matrix**:
| Script Pattern | Required Parameter |
|---------------|-------------------|
| `manage-plan-marshall-config` | `--trace-plan-id` |
| `manage-log` | `--trace-plan-id` |
| `manage-files` | `--plan-id` |
| `manage-tasks` | `--plan-id` |
| `manage-references` | `--plan-id` |
| `manage-solution-outline` | `--plan-id` |
| `manage-assessments` | `--plan-id` |
| `manage-findings` | `--plan-id` |
| `manage-lifecycle` | `--plan-id` |

## pm-invalid-contract-path (PM-005) / pm-contract-non-compliance (PM-006): Contract Implementation Validation

**Requirement**: Skills declaring `implements:` must:
1. Have valid contract path
2. Follow contract requirements

**Check**:
```
IF frontmatter contains implements:
  EXTRACT contract_path
  VERIFY file exists at contract_path
  LOAD contract and verify compliance:
    - Required sections present
    - Output format matches contract
    - Input parameters match contract
```

**Contract Locations**:
- `pm-workflow:manage-solution-outline/standards/deliverable-contract.md`
- `pm-workflow:workflow-extension-api/standards/extensions/*.md`

## Issue Types

| ID | Descriptive Name | Severity | Description |
|----|-----------------|----------|-------------|
| PM-001 | pm-implicit-script-call | error | Script call missing explicit parameters |
| PM-002 | pm-generic-api-reference | error | References API docs instead of explicit call |
| PM-003 | pm-wrong-plan-parameter | error | Uses --plan-id where --trace-plan-id required or vice versa |
| PM-004 | pm-missing-plan-parameter | error | Script call missing required plan parameter |
| PM-005 | pm-invalid-contract-path | error | implements: points to non-existent file |
| PM-006 | pm-contract-non-compliance | warning | Component doesn't follow contract requirements |

## Detection Patterns

### PM-001 (pm-implicit-script-call)

**Regex patterns**:
```
execute-script\.py.*\.\.\.$
execute-script\.py.*\{see.*\}
execute-script\.py[^`]*#\s*See
```

**Context**: Check bash blocks for incomplete parameter specification.

### PM-002 (pm-generic-api-reference)

**Regex patterns**:
```
[Ss]ee\s+\w+\s+API
[Rr]efer\s+to\s+\w+\s+documentation
[Pp]arameters\s+documented\s+in
[Ss]ee\s+\w+\s+for\s+available\s+options
[Ss]ee\s+\w+\s+skill\s+for\s+parameters
```

**Context**: Scan entire document, especially sections near bash blocks.

### PM-003 (pm-wrong-plan-parameter)

**Detection logic**:
1. Extract script name from `execute-script.py {bundle}:{skill}:{script}`
2. Check parameter against matrix above
3. Flag if `--plan-id` used with config/log scripts
4. Flag if `--trace-plan-id` used with data scripts

### PM-004 (pm-missing-plan-parameter)

**Detection logic**:
1. Identify script calls to plan-related scripts
2. Check if any plan parameter (`--plan-id` or `--trace-plan-id`) is present
3. Flag if neither parameter found

### PM-005 (pm-invalid-contract-path)

**Detection logic**:
1. Extract `implements:` value from frontmatter
2. Resolve path (supports notation like `pm-workflow:skill/path`)
3. Check if file exists at resolved path
4. Flag if file not found

### PM-006 (pm-contract-non-compliance)

**Detection logic**:
1. Load contract file
2. Extract required sections/outputs
3. Compare against component content
4. Flag missing requirements

## Fix Strategies

### PM-001 (pm-implicit-script-call) Fix: Add Explicit Parameters

1. Identify the script being called
2. Look up script's `--help` output or documentation
3. Replace ellipsis/reference with explicit parameters
4. Use `{variable_name}` for dynamic values

### PM-002 (pm-generic-api-reference) Fix: Replace with Explicit Call

1. Identify what operation is being referenced
2. Find the correct script command
3. Write complete bash block with all parameters
4. Remove generic reference text

### PM-003 (pm-wrong-plan-parameter) Fix: Swap Parameter

1. Determine correct parameter from matrix
2. Replace `--plan-id` with `--trace-plan-id` or vice versa
3. Verify parameter name matches script expectations

### PM-004 (pm-missing-plan-parameter) Fix: Add Plan Parameter

1. Determine which parameter is needed from matrix
2. Add appropriate `--plan-id {plan_id}` or `--trace-plan-id {plan_id}`
3. Ensure variable name matches context

### PM-005 (pm-invalid-contract-path) Fix: Correct Contract Path

1. Verify the intended contract exists
2. Fix path typos or outdated references
3. If contract doesn't exist, either create it or remove `implements:`

### PM-006 (pm-contract-non-compliance) Fix: Add Missing Contract Requirements

1. Read the contract requirements
2. Add missing sections or outputs
3. Ensure format matches contract specification

## Exemptions

### Scripts Without Plan Parameters

Some scripts don't require plan parameters:
- Utility scripts (format conversion, validation)
- Global configuration scripts
- One-off analysis tools

### Documentation-Only References

API references in documentation sections (not workflow steps) may be acceptable if:
- They reference external documentation
- The component doesn't execute the script directly
- They're in a "See Also" or "References" section

## Validation Workflow

1. **Load component**
2. **Check path**: Is it in `pm-workflow/` or has `implements:` with pm-workflow contract?
3. **If yes, load this guide**
4. **Scan bash blocks**: Apply PM-001, PM-003/PM-004, PM-005/PM-006
5. **Scan full text**: Apply PM-002
6. **Check frontmatter**: Apply PM-005/PM-006 if `implements:` present
7. **Report findings** with severity and fix guidance
