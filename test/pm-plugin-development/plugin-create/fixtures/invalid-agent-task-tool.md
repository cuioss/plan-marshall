---
name: invalid-agent-with-task
description: This agent incorrectly includes the Task tool
tools: Read, Write, Task
---

# Invalid Agent With Task Tool

This agent demonstrates Rule 6 violation - agents cannot use Task tool.

## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this agent and discover a more precise, better, or more efficient approach, **REPORT the improvement to your caller** with improvements.

## Workflow

### Step 1: Read Files
Read input files

### Step 2: Launch Sub-Agent
Task: Launch another agent to process data

### Step 3: Aggregate Results
Combine results

## Tool Usage

**Read**: Load files
**Write**: Write results
**Task**: Launch sub-agents (WRONG - agents cannot use Task)

## Critical Rules

- This is an intentionally invalid agent for testing
