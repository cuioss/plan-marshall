---
name: task-tool-agent
description: Agent that incorrectly declares Task tool
tools: Read, Write, Task, Edit
model: sonnet
---

# Task Tool Agent

This agent declares the Task tool which violates Rule 6.

## Purpose

Agents should not use Task tool to spawn other agents.

## Workflow

1. Read input files
2. Use Task tool to spawn sub-agent (VIOLATION)
3. Edit results
4. Write output

## Why This Is Wrong

Rule 6 prohibits agents from declaring the Task tool because agents should be self-contained and not spawn other agents.
