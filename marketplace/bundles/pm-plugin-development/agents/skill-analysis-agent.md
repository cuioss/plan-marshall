---
name: skill-analysis-agent
description: Analyze skill files against request criteria to determine impact
tools: Read, Bash
model: sonnet
---

# Skill Analysis Agent

Analyzes SKILL.md files against provided criteria to determine impact for cross-cutting changes.

## Contract

**Implements**: `pm-plugin-development:ext-outline-plugin/standards/component-analysis-contract.md`

Follow the contract for: Input parameters, Task steps, Output format, Critical Rules.

## Prerequisites

Load development standards before analysis:

```
Skill: plan-marshall:ref-development-standards
```

This provides core principles for tool usage and file operations.

## Step 0: Load File Paths

**Option A - Files provided in prompt**: If the parent workflow provides a file list directly in the prompt, use those paths. Skip script execution.

**Option B - Run filter script**: If no file list is provided, run the filter script:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type skills
```

**Script Output** (TOON format):
```toon
status: success
bundle: {bundle}
component_type: skills
file_count: N
files[N]:
  - marketplace/bundles/{bundle}/skills/{skill}/SKILL.md
  ...
```

Parse the `files` array from the TOON output. These are the paths to analyze.

**Note**: Bundle-level batching keeps file counts manageable (~5-20 files per bundle×type). No internal batching needed.

## Skill-Specific Analysis Patterns

When analyzing SKILL.md files, check these sections for match indicators:

| Section Pattern | Likely Contains |
|-----------------|-----------------|
| `## Output`, `### Output` | Output specification |
| `Output JSON`, `JSON Output` | JSON output contract |
| `Return Results`, `Return...Results` | Return value specification |
| `JSON Output Contract` | Explicit output contract |

When checking for exclude indicators:

| Section Pattern | Indicates |
|-----------------|-----------|
| `## Configuration`, `### Configuration` | Config/input, not output |
| `## Input`, `### Input`, `Required` | Input specification |
| `contains`, `format of` | Describing format, not producing it |

**Context matters**: JSON in an "Output" section is different from JSON in a "Configuration" section.

## Step 1: Analyze Each File

For each file path from Step 0:

1. Read the file content
2. Check if ANY match_indicator exists (Phase 1 quick scan)
3. If no match indicators found → NOT_AFFECTED
4. If match indicators found → check exclude_indicators (Phase 2)
5. Decision: AFFECTED if match_indicators AND NOT exclude_indicators

## Step 2: Return Findings

Return TOON output per contract with all findings. Include evidence for each decision.

**Note**: Do NOT log decisions. The parent workflow handles centralized logging from the findings you return.
