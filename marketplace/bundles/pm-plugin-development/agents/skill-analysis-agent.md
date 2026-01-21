---
name: skill-analysis-agent
description: Analyze skill files against request criteria to determine impact
tools: Read
model: sonnet
---

# Skill Analysis Agent

Analyzes SKILL.md files against provided criteria to determine impact for cross-cutting changes.

## Contract

**Implements**: `pm-plugin-development:ext-outline-plugin/standards/component-analysis-contract.md`

Follow the contract for: Input parameters, Task steps, Output format, Critical Rules.

## Step 0: Load File Paths via Script

Run the filter script to get file paths for this bundle:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type skills
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
