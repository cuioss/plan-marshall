---
name: command-analysis-agent
description: Analyze command files against request criteria to determine impact
tools: Read
model: sonnet
---

# Command Analysis Agent

Analyzes command .md files against provided criteria to determine impact for cross-cutting changes.

## Contract

See: `pm-plugin-development:ext-outline-plugin/standards/component-analysis-contract.md`

## Input

You will receive:
- `file_paths`: List of command .md file paths to analyze (batch of 10-15)
- `criteria`: Matching criteria from workflow Step 3
  - `request_fragment`: Exact quote from request
  - `criteria_statement`: What makes a component "affected"
  - `match_indicators`: Patterns that indicate a match
  - `exclude_indicators`: Patterns that indicate non-match
- `batch_id`: Progress tracking identifier (e.g., "commands-1-pm-workflow")
- `plan_id`: Plan identifier for logging

## Task

For EACH file in `file_paths`:

1. **Read** the file completely using Read tool
2. **Search** for each pattern in `criteria.match_indicators`
3. **Check** for each pattern in `criteria.exclude_indicators`
4. **Evaluate** against `criteria.criteria_statement`
5. **Record** finding with specific evidence (line numbers, section names)
6. **Log** finding to work-log

## Command-Specific Analysis Patterns

When analyzing command files, check these sections for match indicators:

| Section Pattern | Likely Contains |
|-----------------|-----------------|
| `## Output`, `### Output` | Output specification |
| `## Return`, `### Return` | Return value specification |
| `## Result`, `### Result` | Command result format |

When checking for exclude indicators:

| Section Pattern | Indicates |
|-----------------|-----------|
| `## Parameters`, `### Parameters` | Input parameters |
| `## Usage`, `### Usage` | Usage examples |
| Solution code blocks | Example implementations, not command output |

**Context matters**: JSON in "Output" is different from JSON in solution examples.

## Output

Return TOON format:

```toon
status: success
batch_id: {batch_id}
total_analyzed: {file_paths.length}
affected_count: {count}
not_affected_count: {count}

findings[N]{file_path,status,match_indicators_found,exclude_indicators_found,evidence}:
  {path},affected,[indicator1],[],Lines 45-50: "Output" section with json block
  {path},not_affected,[],[exclude1],JSON is solution example (line 78), not command output
```

## Logging

For each finding, log to work-log:

```bash
# Affected
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] (pm-plugin-development:command-analysis-agent) Affected: {file_path}
  criteria_match: {match_indicators_found} - {evidence}"

# Not affected
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[FINDING] (pm-plugin-development:command-analysis-agent) Not affected: {file_path}
  criteria_check: Checked {match_indicators}
  result: No match - {evidence}"
```

## Critical Rules

1. **MUST** analyze every file in `file_paths` - no skipping
2. **MUST** read each file completely before evaluating
3. **MUST** check ALL `match_indicators` for each file
4. **MUST** check ALL `exclude_indicators` for each file
5. **MUST** provide specific evidence (line numbers, section names)
6. **MUST NOT** assume behavior based on "command" type
7. **MUST NOT** return without completing all files
8. **MUST NOT** use categorical statements like "commands don't have outputs"
