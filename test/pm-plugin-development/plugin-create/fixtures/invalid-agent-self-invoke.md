---
name: invalid-self-invoke-agent
description: This agent incorrectly tries to invoke commands itself
tools: Read, Write
---

# Invalid Self-Invoke Agent

This agent demonstrates Pattern 22 violation - agents should REPORT, not self-invoke.

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this agent and discover a more precise, better, or more efficient approach, **YOU MUST immediately update this file** using `/plugin-update-agent agent-name=invalid-self-invoke-agent update="[your improvement]"` with:
1. Enhanced validation patterns
2. Better error detection
3. Improved reporting clarity
4. Performance optimizations
5. Any lessons learned

This ensures the agent evolves and becomes more effective with each execution.

## Workflow

### Step 1: Analyze Code
Read and analyze code files

### Step 2: Generate Report
Format findings

### Step 3: Self-Update
Invoke /plugin-update-agent to update this file

## Tool Usage

**Read**: Load files
**Write**: Write reports

## Critical Rules

- This is an intentionally invalid agent for testing Pattern 22 violation
- Agent incorrectly tries to self-invoke commands
