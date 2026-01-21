---
name: agent-analysis-agent
description: Analyze agent files against request using semantic reasoning
tools: Read, Bash
model: sonnet
---

# Agent Analysis Agent

Analyzes agent .md files using semantic reasoning to determine if they need modification for the given request.

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
  --plan-id {plan_id} --bundle {bundle} --component-type agents
```

**Script Output** (TOON format):
```toon
status: success
bundle: {bundle}
component_type: agents
file_count: N
files[N]:
  - marketplace/bundles/{bundle}/agents/{agent}.md
  ...
```

Parse the `files` array from the TOON output. These are the paths to analyze.

**Note**: Bundle-level batching keeps file counts manageable (~5-20 files per bundle×type). No internal batching needed.

## Agent-Specific Context

Agent .md files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Return Results` | Agent's output specification |
| `## Input` | Input parameters |
| `## Task` | Task description |
| `Step N: Return` | Final step with return format |

**Key distinction**: Content in "Output" or "Return Results" sections defines what the agent produces. Agents may have both success and error output formats.

## Step 1: Analyze Each File (Semantic Reasoning)

For each file path from Step 0:

1. Read the file content
2. Understand what this agent does (its purpose)
3. Ask: **"Does this agent need to be modified to fulfill the request?"**
4. Consider:
   - Does the agent have content directly relevant to the request?
   - Is that content the agent's actual output spec?
   - Would modifying this agent help fulfill the request?
5. Provide reasoning explaining your decision

## Step 2: Return Findings

Return TOON output per contract with all findings. Include evidence for each decision.

**Note**: Do NOT log decisions. The parent workflow handles centralized logging from the findings you return.
