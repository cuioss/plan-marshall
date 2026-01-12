---
name: over-tooled-agent
description: Agent with unused tools declared
tools: Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, NotebookEdit
model: sonnet
---

# Over-Tooled Agent

This agent declares many tools but only uses a few.

## Purpose

Demonstrate unused tool detection.

## Workflow

1. Use Read tool to read files
2. Use Write tool to write output
3. Use Edit tool for modifications

Note: WebSearch, WebFetch, Glob, Grep, and NotebookEdit are declared but never used.
