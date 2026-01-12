---
name: test-agent-no-model
description: Test agent without optional model field
tools: Read, Grep
---

# Test Agent Without Model

This agent tests that the optional model field can be omitted.

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this agent and discover a more precise, better, or more efficient approach, **REPORT the improvement to your caller** with:
1. Enhanced search patterns
2. Better filtering logic
3. Improved result formatting
4. Performance optimizations
5. Any lessons learned about search workflows

Return structured improvement suggestion in your analysis result:
```
IMPROVEMENT OPPORTUNITY DETECTED
Area: [specific area]
Current limitation: [what doesn't work well]
Suggested enhancement: [specific improvement]
Expected impact: [benefit]
```

The caller can then invoke `/plugin-update-agent agent-name=test-agent-no-model` based on your report.

## Workflow

### Step 1: Search Files
Use Grep to search for patterns

### Step 2: Read Matches
Read files with matches

### Step 3: Generate Report
Format results

## Tool Usage

**Read**: Load matching files
**Grep**: Search for patterns

## Critical Rules

- Handle empty results gracefully
- Return structured output
