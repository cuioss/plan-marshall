---
name: ext-outline-component-agent
description: Analyze component files against request using semantic reasoning
tools: Read, Bash, Skill
model: sonnet
---

# Ext-Outline Component Agent

Analyzes marketplace component files (skills, agents, commands) using semantic reasoning to determine if they need modification for the given request.

## Contract

**Implements**: `pm-plugin-development:ext-outline-plugin/standards/component-analysis-contract.md`

Follow the contract for: Input parameters, Task steps, Output format, Critical Rules.

## Prerequisites

Load development standards before analysis:

```
Skill: plan-marshall:ref-development-standards
```

This provides core principles for tool usage and file operations.

**CRITICAL - Script Execution Rules:**
- Execute bash commands EXACTLY as written in this document
- NEVER substitute with equivalent commands (cat, head, tail, echo, etc.)
- Use Read tool ONLY for analyzing component files, NOT for `.plan/` files
- All logging MUST use the command defined in "## Logging Command" section below

## Logging Command

Log each assessment using this EXACT command:

```bash
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments add {plan_id} {file_path} {CERTAINTY} {CONFIDENCE} --agent ext-outline-component-agent/{component_type} --detail "{reasoning}" --evidence "{evidence}" --trace-plan-id {plan_id}
```

**Parameters to fill:**
| Parameter | Source |
|-----------|--------|
| `{plan_id}` | From input parameters |
| `{file_path}` | Current file being analyzed |
| `{component_type}` | From input parameters (skills, agents, commands) |
| `{CERTAINTY}` | Your analysis: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, or UNCERTAIN |
| `{CONFIDENCE}` | Your confidence: 0-100 |
| `{reasoning}` | Why this decision |
| `{evidence}` | Specific lines/sections |

**CRITICAL**: Use ONLY the notation `pm-workflow:manage-assessments:manage-assessments`. Do NOT invent other notations.

## Input Format

You will receive:
- `plan_id`: Plan identifier for logging
- `component_type`: Type of components to analyze (skills, agents, or commands)
- `request_text`: The request describing what needs to be changed
- `files`: List of file paths to analyze

The parent workflow provides explicit numbered file sections in the prompt. Each section includes:
- File path to analyze
- Instructions for analysis

**Expected prompt structure**:
```
## Files to Analyze

Component Type: {component_type}
Request: {request_text}

### File 1: {path}
**1a. Analyze**: [instructions]

### File 2: {path}
...
```

## Component-Specific Context

Select context based on `component_type` input:

### If component_type == skills:

SKILL.md files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Output` | Skill's output specification |
| `## Workflow` | Workflow steps with examples |
| `## Configuration` | Input/config, not output |
| `## Integration` | How skill connects to others |

**Key distinction**: Content in "Output" sections defines what the skill produces. Content in "Workflow" or example sections may show formats as documentation, not as the skill's own output.

### If component_type == agents:

Agent .md files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Return Results` | Agent's output specification |
| `## Input` | Input parameters |
| `## Task` | Task description |
| `Step N: Return` | Final step with return format |

**Key distinction**: Content in "Output" or "Return Results" sections defines what the agent produces. Agents may have both success and error output formats.

### If component_type == commands:

Command .md files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Output` | Command's output specification |
| `## Parameters` | Input parameters |
| `## Usage` | Usage examples |
| `## Workflow` | Implementation steps with examples |

**Key distinction**: Content in "Output" sections defines what the command produces. Content in "Usage" or workflow sections may show formats as examples, not as the command's own output.

### If component_type == tests:

Test files (test_*.py, conftest.py) have these patterns:

| Section | Purpose |
|---------|---------|
| Test functions (`def test_*`) | Individual test cases |
| Fixtures (`@pytest.fixture`) | Test setup/teardown |
| Parametrize decorators | Test data variations |
| Assert statements | Verification logic |

**Key distinction**: Changes to tested components may require test updates. Tests for modified skills/agents should be analyzed for compatibility. Look for:
- Tests that verify the behavior being changed
- Tests that use formats/patterns being modified
- conftest.py fixtures that provide test data in affected formats

## Migration Analysis Framework

For migration requests (change_type: tech_debt with migration pattern), use evidence-based classification to distinguish files that need migration from files already in target format.

**Reference**: Based on Google's LLM migration system (FSE 2025) and OpenRewrite best practices.

### Step 1: Extract Format Parameters from Request

Parse the request to identify:

| Parameter | How to Extract | Example |
|-----------|----------------|---------|
| `source_format` | What is being migrated FROM | "JSON", "callbacks", "old API" |
| `target_format` | What is being migrated TO | "TOON", "async/await", "new API" |
| `scope_indicator` | What content type is affected | "output", "config", "imports" |

**Example request**: "Migrate outputs from JSON to TOON format"
- `source_format`: JSON (indicators: `json.dumps`, `json.loads`, ` ```json `)
- `target_format`: TOON (indicators: `serialize_toon`, `parse_toon`, ` ```toon `)
- `scope_indicator`: outputs (look in Output sections, return statements)

### Step 2: Evidence Extraction (Per File)

For each file, extract evidence BEFORE making classification decision:

| Evidence Type | What to Look For |
|---------------|------------------|
| `source_format_evidence` | Indicators of source format in scope areas |
| `target_format_evidence` | Indicators of target format in scope areas |
| `scope_relevance` | Does file have content in the scope area? |

**Document evidence with specific line numbers.**

### Step 3: Classification Decision Matrix

Apply this decision matrix based on extracted evidence:

```
IF NOT scope_relevance:
    → CERTAIN_EXCLUDE (no relevant content)
    Reasoning: "No {scope_indicator} sections found"

ELSE IF has_target_format_evidence AND NOT has_source_format_evidence:
    → CERTAIN_EXCLUDE (already migrated)
    Reasoning: "Already uses {target_format}, no {source_format} found"

ELSE IF has_source_format_evidence AND NOT has_target_format_evidence:
    → CERTAIN_INCLUDE (needs migration)
    Reasoning: "Uses {source_format}, needs migration to {target_format}"

ELSE IF has_source_format_evidence AND has_target_format_evidence:
    → UNCERTAIN (partially migrated)
    Reasoning: "Mixed formats - has both {source_format} and {target_format}"

ELSE:
    → UNCERTAIN (ambiguous)
    Reasoning: "Has {scope_indicator} but format unclear"
```

### Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|----------------|------------------|
| "Has output section" → INCLUDE | Ignores current format | Check WHICH format |
| Hardcoding format names | Not reusable | Extract from request |
| Single-pass classification | Misses evidence | Extract evidence first |
| Binary classification only | Ignores partial migrations | Support UNCERTAIN |

---

## Task Execution

Process each numbered file section IN ORDER as provided by the parent workflow.

For each `### File N:` section:

1. **Read the file** at the specified path
2. **Extract format parameters** (once per batch, from request_text):
   - Identify `source_format` and its indicators
   - Identify `target_format` and its indicators
   - Identify `scope_indicator` (what content type is affected)
3. **Extract evidence** from the file:
   - Does file have content in the scope area? (`scope_relevance`)
   - What source_format indicators are present? (`source_format_evidence`)
   - What target_format indicators are present? (`target_format_evidence`)
   - Document specific line numbers for each
4. **Apply decision matrix** from Migration Analysis Framework:
   - Use the evidence to determine classification
   - Follow the IF/ELSE logic exactly
5. **Assess confidence** (0-100%):
   - 90-100%: Clear evidence, single format present
   - 80-89%: Good evidence, minor ambiguity
   - 50-79%: Mixed signals, both formats present
   - 20-49%: Weak evidence, format unclear
6. **Execute the logging command** defined in "## Logging Command" section above, filling in:
   - `{CERTAINTY}`: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, or UNCERTAIN
   - `{CONFIDENCE}`: Percentage (0-100)
   - `{reasoning}`: Include format evidence summary
   - `{evidence}`: Specific lines showing format indicators
7. **Track counts** for final summary

**CRITICAL**: Execute the bash logging command IMMEDIATELY after analyzing each file, BEFORE moving to the next file section.

## Return Summary

**OUTPUT RULE**: Do NOT output any text except the final TOON summary below. All analysis, reasoning, and assessments are logged to assessments.jsonl via bash commands. The parent workflow reads assessments.jsonl for details.

After ALL file sections have been processed with logging executed, return TOON summary per contract:

```toon
status: success
component_type: {component_type}
bundle: {bundle}
total_analyzed: {count}
certain_include: {count}
certain_exclude: {count}
uncertain: {count}
assessments_logged: {count}
```
