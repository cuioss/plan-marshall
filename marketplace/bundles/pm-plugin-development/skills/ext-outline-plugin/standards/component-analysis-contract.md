# Component Analysis Contract

Defines the input/output contract for component analysis agents used in path-multi-workflow Step 4.

## Purpose

Component analysis agents enforce per-component evaluation against request-derived criteria. By delegating to agents with structured contracts, we prevent the parent workflow from skipping component types or making categorical assumptions.

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_paths` | List[str] | Yes | Files to analyze (batches of 10-15) |
| `criteria` | object | Yes | Matching criteria from Step 3 extraction |
| `criteria.request_fragment` | str | Yes | Exact quote from request defining scope |
| `criteria.criteria_statement` | str | Yes | What makes a component "affected" |
| `criteria.match_indicators` | List[str] | Yes | Patterns that indicate a match |
| `criteria.exclude_indicators` | List[str] | Yes | Patterns that indicate non-match |
| `batch_id` | str | Yes | Progress tracking (e.g., "skills-1-pm-workflow") |
| `plan_id` | str | Yes | Plan identifier for logging |

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

## Logging Integration

Agents SHOULD log findings to work-log for audit trail:

```bash
# For affected files
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] ({agent_name}) Affected: {file_path}
  criteria_match: {match_indicators_found} - {evidence}"

# For not-affected files
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] ({agent_name}) Not affected: {file_path}
  criteria_check: {indicators_checked}
  result: No match - {evidence}"
```

## Usage in path-multi-workflow.md

Step 4 spawns agents with this contract:

```markdown
Task:
  subagent_type: pm-plugin-development:skill-analysis-agent
  prompt: |
    Analyze skills against criteria.

    file_paths:
      - marketplace/bundles/pm-workflow/skills/skill-a/SKILL.md
      - marketplace/bundles/pm-workflow/skills/skill-b/SKILL.md

    criteria:
      request_fragment: "Migrate outputs from JSON to TOON"
      criteria_statement: "Component has JSON output specification"
      match_indicators:
        - "```json in Output/Return sections"
        - "Output JSON header"
      exclude_indicators:
        - "```toon already present"
        - "JSON is configuration not output"

    batch_id: skills-1-pm-workflow
    plan_id: migrate-json-to-toon
```

## Implementing Agents

Three agents implement this contract:

| Agent | Component Type | Location |
|-------|----------------|----------|
| `skill-analysis-agent` | SKILL.md files | pm-plugin-development/agents/ |
| `command-analysis-agent` | Command .md files | pm-plugin-development/agents/ |
| `agent-analysis-agent` | Agent .md files | pm-plugin-development/agents/ |

Each agent adds component-type-specific patterns while following the common contract.
