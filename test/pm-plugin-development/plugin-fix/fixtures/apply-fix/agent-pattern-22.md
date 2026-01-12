---
name: self-updating-agent
description: Agent that violates Pattern 22 with self-update
tools: Read, Edit, Write
model: sonnet
---

# Self-Updating Agent

This agent contains a CONTINUOUS IMPROVEMENT section that violates Pattern 22.

## Purpose

Process data and improve itself.

## Workflow

1. Read input
2. Process data
3. Write output

## CONTINUOUS IMPROVEMENT

When you identify improvements to this agent:

1. Use /plugin-update-agent to update this agent directly
2. Make the changes yourself
3. Verify the changes work

This is a Pattern 22 violation - agents should report improvements to caller, not self-update.
