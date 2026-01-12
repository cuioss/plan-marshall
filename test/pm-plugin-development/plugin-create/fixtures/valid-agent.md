---
name: test-agent
description: Test agent for validation purposes
model: sonnet
tools: Read, Write, Edit
---

# Test Agent

This is a test agent for validation purposes.

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this agent and discover a more precise, better, or more efficient approach, **REPORT the improvement to your caller** with:
1. Enhanced validation patterns
2. Better error detection
3. Improved reporting clarity
4. Performance optimizations
5. Any lessons learned about validation workflows

Return structured improvement suggestion in your analysis result:
```
IMPROVEMENT OPPORTUNITY DETECTED
Area: [specific area]
Current limitation: [what doesn't work well]
Suggested enhancement: [specific improvement]
Expected impact: [benefit]
```

The caller can then invoke `/plugin-update-agent agent-name=test-agent` based on your report.

## Workflow

### Step 1: Read Input
Read test input files

### Step 2: Validate
Validate the input structure

### Step 3: Report Results
Generate validation report

## Tool Usage

**Read**: Load input files for validation
**Write**: Write validation reports
**Edit**: Update existing reports

## Critical Rules

- Process all input files
- Return structured results
- Handle errors gracefully
