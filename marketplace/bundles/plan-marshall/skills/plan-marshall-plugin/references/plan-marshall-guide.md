# plan-marshall Validation Guide

Reference guide for validating plan-marshall components and skills implementing plan-marshall contracts.

## When to Load

Load this guide when validating:
- Components in `marketplace/bundles/plan-marshall/`
- Components with `implements:` frontmatter pointing to plan-marshall contracts

## pm-implicit-script-call (PM-001): Explicit Script Commands

**Requirement**: All bash script calls must be explicit with all parameters shown.

**Check**:
```text
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
```text
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
```text
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
```text
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
```text
execute-script\.py.*\.\.\.$
execute-script\.py.*\{see.*\}
execute-script\.py[^`]*#\s*See
```

**Context**: Check bash blocks for incomplete parameter specification.

### PM-002 (pm-generic-api-reference)

**Regex patterns**:
```text
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

### No reachable validation script

⛔ **A validator exists but has no sanctioned invocation, so none may be
documented here.** `_cmd_extension.py`'s `validate_extension` / `scan_extensions`
check the module's structure against most of this contract, but they sit behind
the unregistered, underscore-prefixed `_validate.py` and no pass calls them. See
[extension-contract.md § Validation](../../extension-api/standards/extension-contract.md#validation).

⛔ **The wired verb has an empty population here.** `validate-contracts` selects
implementors by directory-name prefix — `ext-triage-`, `ext-outline-`, `recipe-`,
`build-` (not `build-server`), plus `*_provider.py` scripts — so a
`plan-marshall-plugin` directory is never in its population and
`validate-contracts --skill {bundle}:plan-marshall-plugin` returns
`total_checked: 0` with `status: success`: well-formed, and measuring nothing.
The manifest's `implements:` declaration does not put it in scope; that field is
something the validator checks, not how it picks what to check.

In practice, then, the functions are checked by **reading the module against the
two tables below**. Runtime does exercise them, but that is not a substitute for
the reading, because the failure handling is not uniform. A hook may be reached
from one place or from several, and the handling differs from site to site, so
the same failure surfaces differently — or not at all — depending on which verb
ran. Examples, not an enumeration:

- `extension_discovery.py`'s `get_skill_domains_from_extensions()` and
  `discover_applicable_extensions()` log a WARNING through `log_entry`.
- On the `apply-config-defaults` path, a failing `discover_modules()` is swallowed
  whole (`except Exception: extensions_skipped += 1; continue`, no log), while a
  failing `config_defaults()` a few lines later IS collected into
  `results['errors']` and surfaces as `status: error`.
- `get_workflow_extensions_from_extensions()` runs `provides_triage()` and
  `provides_outline_skill()` under a bare `except Exception: pass`.
- `manage-config`'s `_cmd_skill_domains.py` calls `get_skill_domains()`,
  `provides_triage()`, `provides_outline_skill()`, and `provides_recipes()` under
  a single `try` whose handler PRINTS to stderr rather than logging — and other
  helpers in that same file swallow the identical failure with
  `except Exception: continue`.

`discover_all_extensions()` itself calls none of them — it resolves the path,
imports the module, and instantiates `Extension()` (which runs whatever the
class's `__init__` does).

⛔ **So the absence of a diagnostic is not evidence that a hook works.** It may
mean the hook is fine, or that the one path which would have complained never
ran. That is the same false-green shape as the empty-population call above, and
it is why the reading below is the actual check.

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

Valid profile names, as recognised by `_cmd_extension.py`'s
`VALID_PROFILE_CATEGORIES`: `core`, `implementation`, `module_testing`,
`integration_testing`, `quality`, `documentation`.

⛔ **A name outside that set is not an error — it is a skipped check.** The
validator reports `unknown_category` at severity `warning` (which does not fail)
and then skips the profile, so the `defaults` / `optionals` structure check
silently does not run for it. `testing` is the name most likely to be written by
mistake; the contract name is `module_testing`.

### Integration with doctor-skills

When `skill-name` matches `plan-marshall-plugin`:

1. **Standard analysis**: the structure, markdown, and reference checks that
   `doctor-marketplace analyze` runs for any skill. The underlying modules
   (`_analyze.py`, `_validate.py`) are not registered scripts and have no
   sanctioned executor form, so they are not invoked by name here.
2. **Extension validation**: read the module against the two tables above. There
   is no invocation to run — see [§ No reachable validation script](#no-reachable-validation-script)
   for the validator that exists and why nothing reaches it.
3. **Report**: record what the reading established, categorise as safe/risky, and
   auto-apply safe fixes.
