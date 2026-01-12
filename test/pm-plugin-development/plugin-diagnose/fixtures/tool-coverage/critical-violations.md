---
name: critical-violations
description: Agent with critical violations
tools: Read, Task, Write
model: sonnet
---

# Critical Violations Agent

This agent has multiple critical issues.

## Step 1: Read Files

Use the Read tool to read configuration files.

## Step 2: Invoke Maven

Execute Maven build:
```bash
Bash: ./mvnw clean install
```

## Step 3: Create Backup

Save backup file to myfile.backup before making changes.

## Step 4: Delegate Work

Use Task tool with subagent_type="other-agent" to delegate work.

## Step 5: Write Output

Use the Write tool to create output.old file.
