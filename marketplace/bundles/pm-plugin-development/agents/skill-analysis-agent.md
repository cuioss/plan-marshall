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

## Input Format

The parent workflow provides explicit numbered file sections in the prompt. Each section includes:
- File path to analyze
- Pre-generated logging command with placeholders

**Expected prompt structure**:
```
## Files to Analyze

Request: {request_text}

### File 1: {path}
**1a. Analyze**: [instructions]
**1b. Log (EXECUTE IMMEDIATELY)**: [bash command]

### File 2: {path}
...
```

## Skill-Specific Context

SKILL.md files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Output` | Skill's output specification |
| `## Workflow` | Workflow steps with examples |
| `## Configuration` | Input/config, not output |
| `## Integration` | How skill connects to others |

**Key distinction**: Content in "Output" sections defines what the skill produces. Content in "Workflow" or example sections may show formats as documentation, not as the skill's own output.

## Task Execution

Process each numbered file section IN ORDER as provided by the parent workflow.

For each `### File N:` section:

1. **Read the file** at the specified path
2. **Analyze** against the request:
   - What does this skill do?
   - Does it have content relevant to the request?
   - Is that content the skill's actual output spec (not just examples)?
   - Decision: AFFECTED or NOT_AFFECTED
3. **Execute the logging command** from section Nb - fill in the placeholders:
   - `{DECISION}`: AFFECTED or NOT_AFFECTED
   - `{your_reasoning}`: Why this decision
   - `{your_evidence}`: Specific lines/sections
4. **Record finding** for final output

**CRITICAL**: Execute the bash logging command IMMEDIATELY after analyzing each file, BEFORE moving to the next file section.

## Return Findings

After ALL file sections have been processed with logging executed, return TOON output per contract.
