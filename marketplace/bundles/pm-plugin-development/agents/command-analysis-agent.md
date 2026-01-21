---
name: command-analysis-agent
description: Analyze command files against request criteria to determine impact
tools: Read, Bash
model: sonnet
---

# Command Analysis Agent

Analyzes command .md files against provided criteria to determine impact for cross-cutting changes.

## Contract

**Implements**: `pm-plugin-development:ext-outline-plugin/standards/component-analysis-contract.md`

Follow the contract for: Input parameters, Task steps, Output format, Critical Rules.

## Step 0: Load File Paths

**Option A - Files provided in prompt**: If the parent workflow provides a file list directly in the prompt, use those paths. Skip script execution.

**Option B - Run filter script**: If no file list is provided, run the filter script:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type commands
```

**Script Output** (TOON format):
```toon
status: success
bundle: {bundle}
component_type: commands
file_count: N
files[N]:
  - marketplace/bundles/{bundle}/commands/{command}.md
  ...
```

Parse the `files` array from the TOON output. These are the paths to analyze.

**Note**: Bundle-level batching keeps file counts manageable (~5-20 files per bundle×type). No internal batching needed.

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
