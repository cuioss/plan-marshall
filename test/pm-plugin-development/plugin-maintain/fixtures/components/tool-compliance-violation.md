---
name: tool-compliance-violation
description: An agent with tool compliance issues
tools: Read, Write, Task
model: sonnet
---

# Tool Compliance Violation Agent

This agent violates Rule 6 by declaring Task tool.

## Purpose

Demonstrates tool compliance violations.

## Workflow

### Step 1: Analyze

Read and analyze the target.

### Step 2: Delegate

Use Task tool to spawn sub-agents (Rule 6 violation).

### Step 3: Report

Compile results.

## Examples

### Example 1

```bash
/tool-compliance-violation target=file.md
```
