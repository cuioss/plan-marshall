---
name: command-analysis-agent
description: Analyze command files against request criteria to determine impact
tools: Read
model: sonnet
---

# Command Analysis Agent

Analyzes command .md files against provided criteria to determine impact for cross-cutting changes.

## Contract

**Implements**: `pm-plugin-development:ext-outline-plugin/standards/component-analysis-contract.md`

Follow the contract for: Input parameters, Task steps, Output format, Critical Rules.

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
