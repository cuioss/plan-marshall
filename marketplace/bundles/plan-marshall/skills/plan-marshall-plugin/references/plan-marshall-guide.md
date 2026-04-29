# plan-marshall Validation Guide

Reference guide for validating plan-marshall components and skills implementing plan-marshall contracts.

## When to Load

Load this guide when validating:
- Components in `marketplace/bundles/plan-marshall/`
- Components with `implements:` frontmatter pointing to plan-marshall contracts

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
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \
  --plan-id {plan_id} \
  --task-number {task_number}
```

**Invalid**:
```bash
# See manage-tasks API for parameters
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read ...
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

## pm-wrong-plan-parameter (PM-003) / pm-missing-plan-parameter (PM-004): Correct plan-id vs audit-plan-id Usage

**Requirement**: Plan-related components must use correct parameter:
- `--plan-id`: For data operations (read/write plan files, artifacts)
- `--audit-plan-id`: For config lookups and logging context

**Check**:
```
FOR each script call:
  IF script is manage-config:
    REQUIRE --audit-plan-id (not --plan-id)
  IF script is manage-log:
    REQUIRE --audit-plan-id for context
  IF script is manage-files, manage-tasks, manage-references:
    REQUIRE --plan-id for data operations
```

**Parameter Matrix**:
| Script Pattern | Required Parameter |
|---------------|-------------------|
| `manage-config` | `--audit-plan-id` |
| `manage-log` | `--audit-plan-id` |
| `manage-files` | `--plan-id` |
| `manage-tasks` | `--plan-id` |
| `manage-references` | `--plan-id` |
| `manage-solution-outline` | `--plan-id` |
| `manage-assessments` | `--plan-id` |
| `manage-findings` | `--plan-id` |
| `manage-status` | `--plan-id` |

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
- `plan-marshall:manage-solution-outline/standards/solution-outline-standard.md`
- `plan-marshall:extension-api/standards/*.md`

## Issue Types

| ID | Descriptive Name | Severity | Description |
|----|-----------------|----------|-------------|
| PM-001 | pm-implicit-script-call | error | Script call missing explicit parameters |
| PM-002 | pm-generic-api-reference | error | References API docs instead of explicit call |
| PM-003 | pm-wrong-plan-parameter | error | Uses --plan-id where --audit-plan-id required or vice versa |
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
4. Flag if `--audit-plan-id` used with data scripts

### PM-004 (pm-missing-plan-parameter)

**Detection logic**:
1. Identify script calls to plan-related scripts
2. Check if any plan parameter (`--plan-id` or `--audit-plan-id`) is present
3. Flag if neither parameter found

### PM-005 (pm-invalid-contract-path)

**Detection logic**:
1. Extract `implements:` value from frontmatter
2. Resolve path (supports notation like `plan-marshall:skill/path`)
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
2. Replace `--plan-id` with `--audit-plan-id` or vice versa
3. Verify parameter name matches script expectations

### PM-004 (pm-missing-plan-parameter) Fix: Add Plan Parameter

1. Determine which parameter is needed from matrix
2. Add appropriate `--plan-id {plan_id}` or `--audit-plan-id {plan_id}`
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
2. **Check path**: Is it in `plan-marshall/` or has `implements:` with plan-marshall contract?
3. **If yes, load this guide**
4. **Scan bash blocks**: Apply PM-001, PM-003/PM-004, PM-005/PM-006
5. **Scan full text**: Apply PM-002
6. **Check frontmatter**: Apply PM-005/PM-006 if `implements:` present
7. **Report findings** with severity and fix guidance

## plan-marshall-plugin Extension Validation

Applies when doctoring a skill where `name` equals `plan-marshall-plugin` and contains an `extension.py` implementing the Extension API.

### Validation Script

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate extension \
  --bundle {bundle_name}
```

Extract bundle name from skill path: `marketplace/bundles/{bundle}/skills/plan-marshall-plugin`

### Required Functions

| Function | Description | Fix Type |
|----------|-------------|----------|
| `get_skill_domains()` | Domain metadata with profiles | Safe |

### Optional Functions

| Function | Description | Fix Type |
|----------|-------------|----------|
| `discover_modules()` | Project module discovery | Safe |
| `config_defaults()` | Project configuration defaults | Safe |
| `provides_triage()` | Triage skill reference | Risky |
| `provides_outline_skill()` | Domain-specific outline skill reference | Risky |

### Profile Structure

`get_skill_domains()` must return objects with:
- `domain.key` — Domain identifier (kebab-case)
- `domain.name` — Human-readable name
- `profiles.core` — Core profile (required)
- Each profile has `defaults` and `optionals` arrays

Valid profile names: `core` (required), `implementation`, `testing`, `quality`.

### Integration with doctor-skills

When `skill-name` matches `plan-marshall-plugin`:

1. **Standard analysis**: Run `analyze.py structure` + `analyze.py markdown` + `validate.py references`
2. **Extension validation**: Run extension validation script (see above)
3. **Report**: Include extension validation status, categorize as safe/risky, auto-apply safe fixes
