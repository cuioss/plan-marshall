# Component Analysis Contract

Defines the input/output contract for component analysis agents used in the Modify Flow of `workflow.md`.

## Purpose

Component analysis agents enforce per-component evaluation against request-derived criteria. By delegating to agents with structured contracts, we prevent the parent workflow from skipping component types or making categorical assumptions.

## Input Parameters

Agents receive minimal parameters. File paths are loaded via script.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | str | Yes | Plan identifier for script access and logging |
| `bundle` | str | Yes | Bundle name to analyze (e.g., `pm-dev-java`) |
| `criteria` | object | Yes | Matching criteria from extraction step |
| `criteria.request_fragment` | str | Yes | Exact quote from request defining scope |
| `criteria.criteria_statement` | str | Yes | What makes a component "affected" |
| `criteria.match_indicators` | List[str] | Yes | Patterns that indicate a match |
| `criteria.exclude_indicators` | List[str] | Yes | Patterns that indicate non-match |

## Agent Step 0: Load File Paths via Script

Each agent runs the filter script to get its file paths:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type {skills|commands|agents}
```

**Output** (TOON):
```toon
status: success
bundle: pm-dev-java
component_type: skills
file_count: 17
files[17]:
  - marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
  - ...
```

Parse the `files` array. These are the paths to analyze.

**Note**: Bundle-level batching keeps file counts manageable (~5-20 files per bundle×type). No internal batching needed.

## Output Contract

All analysis agents MUST return this structure:

```toon
status: success
batch_id: {batch_id}
total_analyzed: {file_paths.length}
affected_count: {count}
not_affected_count: {count}

findings[N]{file_path,status,match_indicators_found,exclude_indicators_found,evidence}:
  {path},affected,[indicator1],[],Lines 45-50 contain JSON output block
  {path},not_affected,[],[exclude1],Already uses TOON format in Return section
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `success` or `error` |
| `batch_id` | str | Echo of input batch_id |
| `total_analyzed` | int | Must equal `file_paths.length` |
| `affected_count` | int | Files matching criteria |
| `not_affected_count` | int | Files not matching criteria |
| `findings` | table | One row per file analyzed |

### Finding Fields

| Field | Description |
|-------|-------------|
| `file_path` | Full path to analyzed file |
| `status` | `affected` or `not_affected` |
| `match_indicators_found` | Which match_indicators were found (empty if none) |
| `exclude_indicators_found` | Which exclude_indicators were found (empty if none) |
| `evidence` | Specific line numbers, section names, or content excerpts |

## Validation Rules

The calling workflow MUST validate agent output:

1. **Completeness**: `findings.length == file_paths.length` - no skipping
2. **Evidence required**: Each finding MUST have `evidence` populated
3. **Consistency**: `affected_count + not_affected_count == total_analyzed`
4. **Status check**: `status` must be `success` for results to be used

### Validation Failure Handling

If validation fails:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} ERROR "[VALIDATION] (pm-plugin-development:ext-outline-plugin) Agent validation failed: {batch_id}
  expected_findings: {file_paths.length}
  actual_findings: {findings.length}
  action: Retry or escalate"
```

## Agent Implementation Requirements

### Critical Rules

1. **MUST** analyze every file in `file_paths` - no skipping allowed
2. **MUST** read each file completely before evaluating
3. **MUST** check ALL `match_indicators` for each file
4. **MUST** check ALL `exclude_indicators` for each file
5. **MUST** provide specific evidence (line numbers, section names)
6. **MUST NOT** assume behavior based on component type name
7. **MUST NOT** return without completing all files
8. **MUST NOT** use categorical exclusions

### Analysis Algorithm (Two-Phase)

**CRITICAL**: Use two-phase analysis to avoid false positives.

```
FOR each file_path in file_paths:
  content = READ(file_path)

  # PHASE 1: Quick Match Indicator Scan
  # Check if ANY match_indicator pattern exists in content
  any_match_possible = FALSE
  FOR each indicator in criteria.match_indicators:
    IF contains_pattern(content, indicator):
      any_match_possible = TRUE
      BREAK

  IF NOT any_match_possible:
    # No match indicators found - file cannot be affected
    findings.append({
      file_path,
      status: "not_affected",
      match_found: [],
      exclude_found: [],
      evidence: "No match indicators found in file"
    })
    CONTINUE to next file

  # PHASE 2: Context Analysis (only if match possible)
  match_found = []
  exclude_found = []

  FOR each indicator in criteria.match_indicators:
    IF indicator found in content:
      match_found.append(indicator)
      record_evidence(indicator, location)

  FOR each indicator in criteria.exclude_indicators:
    IF indicator found in content:
      exclude_found.append(indicator)
      record_evidence(indicator, location)

  # Decision: Match indicators found AND no exclude indicators
  IF match_found AND NOT exclude_found:
    status = "affected"
  ELSE:
    status = "not_affected"

  findings.append({file_path, status, match_found, exclude_found, evidence})
```

**Key Points**:
1. **Phase 1 is mandatory** - quickly eliminates files with no match indicators
2. **Phase 2 only runs if match possible** - avoids wasted context analysis
3. **Evidence must be specific** - line numbers and section names

## Usage in Modify Flow

The Modify Flow in `workflow.md` Step 4 uses analysis agents implementing this contract:

```markdown
Skill: pm-plugin-development:component-analysis-dispatch

Input:
  plan_id: migrate-json-to-toon
  inventory: [file list from scan-marketplace-inventory]
  criteria:
    request_fragment: "Migrate outputs from JSON to TOON"
    criteria_statement: "Component has JSON output specification"
    match_indicators:
      - "```json in Output/Return sections"
      - "Output JSON header"
    exclude_indicators:
      - "```toon already present"
      - "JSON is configuration not output"
```

## Implementation

The `component-analysis-dispatch` skill implements this contract:

| Skill | Purpose | Location |
|-------|---------|----------|
| `component-analysis-dispatch` | Unified analysis for all component types | pm-plugin-development/skills/ |

The skill dispatches to type-specific patterns (skills, commands, agents) while following the common contract.
