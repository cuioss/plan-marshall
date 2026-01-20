# Path-Multi Workflow

Workflow for cross-cutting changes that affect shared patterns, interfaces, or conventions across multiple components.

## Step 1: Receive Scope from Assessment Protocol

The following are provided by Assessment Steps 1-3 and MUST be used:

| Input | Source | Description |
|-------|--------|-------------|
| `affected_artifacts` | Step 1.6 | Component types to scan (e.g., [Skills, Agents]) |
| `bundle_scope` | Step 2.3 | Bundles to scan (e.g., "all" or [pm-dev-java, pm-workflow]) |

**CRITICAL**: Do NOT re-derive scope. Use the values from Steps 1-2 directly to constrain:
1. The inventory scan parameters
2. Which components are analyzed

```
LOG: [STATUS] Using scope from initial analysis:
  affected_artifacts: {affected_artifacts}
  bundle_scope: {bundle_scope}
```

## Critical Requirement

Goals MUST contain explicit file paths. A goal that says "update all X" without listing the files is INVALID - it just restates the request.

## Step 2: Load Marketplace Inventory

**CRITICAL**: Use the `scan-marketplace-inventory` script for component discovery. Do NOT use ad-hoc Glob/Grep for this purpose.

**Note**: Use `--trace-plan-id` for plan-scoped logging (the script doesn't have its own `--plan-id` parameter).

### Use Step 1 Outputs for Scan Parameters

The inventory scan MUST use the pre-determined scope from Step 1:

```bash
# Build scan parameters from Step 1 outputs
resource_types = affected_artifacts  # From Step 1
bundles = bundle_scope               # From Step 1

LOG: [STATUS] Executing inventory scan with pre-determined scope:
  resource_types: {resource_types}
  bundles: {bundles}
```

**CRITICAL**: Do NOT re-derive scope here. Use the exact values from Step 1.

### Execute Inventory Scan

```bash
# Use affected_artifacts to filter resource types
# Use bundle_scope to filter bundles (use "all" if bundle_scope == "all")
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {affected_artifacts}  # From Step 1
  --bundles {bundle_scope}               # From Step 1 (or omit if "all")
  --include-descriptions
```

### Link Inventory to References

After scan completes, record the scan parameters in references.toon:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field inventory_scan \
  --value "{timestamp}:{resource-types}:{bundle-filter}"
```

## Step 3: Extract Request Matching Criteria

**Purpose**: Before analyzing components, extract explicit criteria that define "what makes a component affected" based on the REQUEST text. These criteria constrain ALL subsequent per-component analysis.

**CRITICAL**: This step is MANDATORY. Skipping to Step 4 without completing this step is a workflow violation.

### Derive Criteria from Request

Analyze the request text to extract:

1. **Request fragment**: The specific phrase that defines the change scope
2. **Criteria statement**: What makes a component "affected" - in objective terms
3. **Match indicators**: Concrete patterns/elements that indicate a match
4. **Exclude indicators**: Patterns that explicitly exclude a component

```
ANALYZE request text:
  1. Identify the ACTION (migrate, rename, update, change)
  2. Identify the SUBJECT (what is being changed - format, notation, pattern)
  3. Identify the SCOPE (outputs, references, usages)

Derive:
  request_fragment = "{exact quote from request}"
  criteria = "{subject} in {scope} context"
  match_indicators = [concrete patterns that indicate match]
  exclude_indicators = [concrete patterns that indicate non-match]
```

### Log Matching Criteria

Before proceeding to component analysis, log the derived criteria:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[DECISION] (pm-plugin-development:ext-outline-plugin) Request Matching Criteria:
  request_fragment: \"{request_fragment}\"
  criteria: \"{criteria}\"
  match_indicators: {match_indicators}
  exclude_indicators: {exclude_indicators}"
```

### Criteria Quality Validation

The extracted criteria MUST be:

| Requirement | Valid | Invalid |
|-------------|-------|---------|
| **Derived from request** | "Has JSON output blocks" (from "migrate outputs from JSON") | "Is a knowledge document" (assumption) |
| **Objective** | "Contains ```json in Output section" | "Seems to use JSON" |
| **Testable** | grep pattern or section presence | Subjective judgment |

**Anti-patterns (PROHIBITED):**
```
criteria: "Component could be affected"     # Too vague
criteria: "Skills are documentation"        # Categorical assumption
criteria: "Outputs data"                    # Not derived from request
exclude_indicators: ["Skills", "Commands"]  # NEVER use component TYPES as exclude indicators
```

**CRITICAL**: Match and exclude indicators must describe CONTENT characteristics, never COMPONENT TYPES.

| WRONG (component type) | CORRECT (content characteristic) |
|------------------------|----------------------------------|
| `"Skills (knowledge documents)"` | `"JSON is configuration not output"` |
| `"Commands don't have outputs"` | `"No Output/Return section found"` |
| `"Agents already migrated"` | `"Already uses TOON format"` |

The criteria determine WHAT to look for. Step 4 applies those criteria to EACH component regardless of type. Component type filtering was already done in Step 1 (affected_artifacts).

### Persist Criteria for Analysis

After logging, the criteria become the **benchmark** for all Step 4 findings. Every `[FINDING]` log MUST reference these criteria.

## Step 4: Analyze Each Component

### Batch Processing

Process components in batches of **10-15 files** per bundle. After each batch:

1. Log a checkpoint to work-log
2. Review findings before continuing
3. Do NOT skip components or rush through batches

```bash
# After each batch of 10-15 components
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-plugin-development:ext-outline-plugin) Analyzed {component_type} batch {N} of {bundle}: {X} affected, {Y} not affected"
```

**All component types must have batch checkpoints** - if inventory includes agents, commands, AND skills, all three types must show batch progress logs.

### Per-Component Analysis

For each component, execute these steps **in order**:

1. **Read** the component file completely
2. **Search** for match indicators from Step 3 criteria
3. **Check** for exclude indicators from Step 3 criteria
4. **Evaluate** against the criteria statement (not generic assumptions)
5. **Record** the result with criteria reference

**Analysis checklist per component** (derived from Step 3):
- [ ] Does it contain any `match_indicators`?
- [ ] Does it contain any `exclude_indicators`?
- [ ] Does it satisfy the `criteria` statement?
- [ ] What specific evidence supports the finding?

**CRITICAL**: The checklist items are populated FROM the Step 3 criteria extraction. Do NOT use categorical statements without referencing the specific criteria derived from the request.

### Checklist Enforcement Rules

**CRITICAL**: The analysis checklist MUST be applied to EVERY component in `affected_artifacts` from `bundle_scope`.

1. **Scope already determined**: Components outside `affected_artifacts` or `bundle_scope` are SKIPPED (not analyzed). Only analyze what Step 1 identified.

2. **One [FINDING] per component**: Every component within scope gets its own `[FINDING]` log entry - either "Affected" or "Not affected" with component-specific reasoning.

3. **Reference Step 3 criteria**: Findings must explain why based on the criteria extracted in Step 3, not categorical assumptions.

**Anti-pattern (INVALID):**
```
[FINDING] Skills analysis complete: Skills are knowledge documents without output formats
```

**Correct pattern:**
```
[FINDING] Affected: {path}
  criteria_match: {which match_indicator triggered} - {evidence}

[FINDING] Not affected: {path}
  criteria_check: {which indicators were checked}
  result: No match - {specific evidence of non-match}
```

### Logging Affected Files

For each **affected** file, log immediately:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] (pm-plugin-development:ext-outline-plugin) Affected: {file_path}
  criteria_match: {which match_indicator} - {evidence}"
```

**Build affected files list** as you analyze:
```
affected_files:
  bundle-a:
    - path/to/file1.md (criteria_match: {indicator} - {evidence})
    - path/to/file2.md (criteria_match: {indicator} - {evidence})
  bundle-b:
    - path/to/file3.md (criteria_match: {indicator} - {evidence})
```

### Document Excluded Components

For files analyzed but NOT affected, log with criteria reference:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] (pm-plugin-development:ext-outline-plugin) Not affected: {file}
  criteria_check: {which indicators were checked}
  result: No match - {specific evidence}"
```

The rationale should explain WHY the component does not match the Step 3 criteria:
- What match_indicators were checked?
- What exclude_indicators were found?
- Why does it not satisfy the criteria statement?

Example patterns:
- `Checked for "{match_indicator}" - not found in Output sections`
- `Found "{exclude_indicator}" - already uses TOON format`
- `JSON present but context is "Configuration" not "Output" (exclude_indicator)`

### Final Verification

After all batches complete, log the summary:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[MILESTONE] (pm-plugin-development:ext-outline-plugin) Impact analysis complete: {total_affected} of {total_analyzed} affected"
```

### Link Affected Files to References

After analysis complete, persist affected files for execute phase:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references add-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "{comma-separated-paths}"
```

## Step 5: Build Deliverables Section with Enumeration

**Deliverable Organization**: Create one deliverable per bundle (or per ~5-8 files if a bundle has many). Each deliverable MUST list the specific files to modify.

**Deliverable Requirements** (all fields mandatory for Path-Multi):

| Field | Description | Example |
|-------|-------------|---------|
| `files` | Explicit list of file paths | `marketplace/bundles/pm-workflow/agents/solution-outline-agent.md` |
| `change_per_file` | What changes in each file | "Replace ```json output blocks with ```toon" |
| `verification` | How to verify the change | "Grep for ```json returns 0 matches" |

### Deliverable Template

```markdown
### 1. Update {bundle} {component-type}s for {change}

**Metadata:**
- change_type: migrate
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- profile: implementation
- depends: none

**Affected files:**
- `{path/to/file1.md}`
- `{path/to/file2.md}`
- `{path/to/file3.md}`

**Change per file:** {specific change description}

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component {path}`
- Criteria: No quality issues detected

**Success Criteria:**
- {criterion 1}
- {criterion 2}
```

### Valid Example

```markdown
### 1. Update pm-workflow agents to TOON output

**Affected files:**
- `marketplace/bundles/pm-workflow/agents/plan-init-agent.md`
- `marketplace/bundles/pm-workflow/agents/solution-outline-agent.md`
- `marketplace/bundles/pm-workflow/agents/task-plan-agent.md`

**Change per file:** Replace output format from JSON to TOON in Return/Output sections
**Verification:** grep -l 'status: success' returns all files, grep -l '"status":' returns none

**Success Criteria:**
- All agents use TOON output format
- No JSON output blocks remain
```

### Anti-pattern (INVALID)

```markdown
### 1. Update agent output formats to TOON

Migrate all agent .md files to specify TOON output format
```
This restates the request without enumeration. The solution outline phase added no information.

## Decomposition Patterns

| Request Pattern | Typical Deliverables |
|-----------------|----------------------|
| "Rename notation X to Y" | 1. Update core definition 2-N. Update each referencing component |
| "Change output format" | 1. Define new format 2-N. Update each producer/consumer |
| "Migrate to new API" | 1. Implement new API 2-N. Migrate each caller |
