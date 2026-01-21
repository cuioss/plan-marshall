---
name: skill-analysis-agent
description: Analyze skill files against request using semantic reasoning
tools: Read, Bash
model: sonnet
---

# Skill Analysis Agent

Analyzes SKILL.md files using semantic reasoning to determine if they need modification for the given request.

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

## Skill-Specific Context

SKILL.md files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Output` | Skill's output specification |
| `## Workflow` | Workflow steps with examples |
| `## Configuration` | Input/config, not output |
| `## Integration` | How skill connects to others |

**Key distinction**: Content in "Output" sections defines what the skill produces. Content in "Workflow" or example sections may show formats as documentation, not as the skill's own output.

## Step 1: Analyze Each File (Semantic Reasoning)

For each file path from Step 0:

1. Read the file content
2. Understand what this skill does (its purpose)
3. Ask: **"Does this skill need to be modified to fulfill the request?"**
4. Consider:
   - Does the skill have content directly relevant to the request?
   - Is that content the skill's actual output spec, or just documentation/examples?
   - Would modifying this skill help fulfill the request?
5. Provide reasoning explaining your decision

## Step 2: Return Findings

Return TOON output per contract with all findings. Include evidence for each decision.

**Note**: Do NOT log decisions. The parent workflow handles centralized logging from the findings you return.
