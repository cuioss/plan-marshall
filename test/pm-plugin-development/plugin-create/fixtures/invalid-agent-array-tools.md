---
name: array-syntax-agent
description: This agent uses array syntax for tools (should warn but not fail)
tools: [Read, Write, Edit]
---

# Array Syntax Agent

This agent uses array syntax for tools field. This should generate a warning but not fail validation (for compatibility).

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this agent and discover a more precise, better, or more efficient approach, **REPORT the improvement to your caller** with:
1. Enhanced processing logic
2. Better validation
3. Improved output formatting
4. Performance optimizations
5. Any lessons learned

Return structured improvement suggestion in your analysis result:
```
IMPROVEMENT OPPORTUNITY DETECTED
Area: [specific area]
Current limitation: [what doesn't work well]
Suggested enhancement: [specific improvement]
Expected impact: [benefit]
```

The caller can then invoke `/plugin-update-agent agent-name=array-syntax-agent` based on your report.

## Workflow

### Step 1: Read Input
Read input files

### Step 2: Process Data
Process the data

### Step 3: Write Output
Write results

## Tool Usage

**Read**: Load files
**Write**: Write files
**Edit**: Modify files

## Critical Rules

- This agent should generate a warning about tools format
- But should still be considered valid (for compatibility)
