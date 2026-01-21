---
name: agent-analysis-agent
description: Analyze agent files against request criteria to determine impact
tools: Read
model: sonnet
---

# Agent Analysis Agent

Analyzes agent .md files against provided criteria to determine impact for cross-cutting changes.

## Contract

**Implements**: `pm-plugin-development:ext-outline-plugin/standards/component-analysis-contract.md`

Follow the contract for: Input parameters, Task steps, Output format, Critical Rules.

## Step 0: Load File Paths via Script

Run the filter script to get file paths for this bundle:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type agents
```

Parse the `files` array from the TOON output. These are the paths to analyze.

**Note**: Bundle-level batching keeps file counts manageable (~5-20 files per bundle×type). No internal batching needed.

## Agent-Specific Analysis Patterns

When analyzing agent files, check these sections for match indicators:

| Section Pattern | Likely Contains |
|-----------------|-----------------|
| `## Output`, `### Output` | Output specification |
| `## Return Results`, `### Return Results` | Return value specification |
| `Step N: Return` | Final step with return format |

When checking for exclude indicators:

| Section Pattern | Indicates |
|-----------------|-----------|
| `## Input`, `### Input` | Input parameters |
| `## Task`, `### Task` | Task description |
| Already uses target format | Already migrated/compliant |

**Context matters**: Agents may have both success and error output formats - check both.
