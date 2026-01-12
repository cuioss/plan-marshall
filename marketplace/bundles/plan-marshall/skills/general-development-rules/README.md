# CUI General Development Rules Skill

Core development principles that guide all work in CUI projects.

## Overview

This skill provides foundational rules that apply across ALL development activities in CUI projects. It defines when to ask users, how to research best practices, proper tool usage, document management, and dependency approval requirements.

## What's Included

### Standards File

**general-development-rules.md** - Core development principles
- User interaction guidelines (when to ask vs proceed)
- Research requirements (using research-best-practices agent)
- Tool usage standards (Read, Write, Edit vs cat, tail, find)
- Document proliferation guidelines
- Dependency management rules

## Key Features

### Cross-Cutting Principles

All CUI development work follows these rules:
- Ask when in doubt (never guess)
- Research current best practices using research-best-practices agent
- Use proper tools for file operations
- Don't proliferate documents
- Get approval before adding dependencies

### Integration Points

**Delegates to research-best-practices agent:**
- For finding current best practices
- For researching technologies/frameworks
- For discovering latest recommendations

**References diagnostic-patterns skill:**
- For detailed tool usage patterns
- For non-prompting file operations
- For error handling strategies

## Quick Decision Guide

**Should I ask the user?**
- If uncertain about requirements → YES
- If unclear about approach → YES
- If guessing would be needed → YES
- If creative interpretation needed → YES

**Should I research this?**
- Need current best practices → Use research-best-practices agent
- Unfamiliar technology/framework → Use research-best-practices agent
- Want latest recommendations → Use research-best-practices agent

**Which tool should I use?**
- File discovery → Glob (not find or ls)
- Existence checks → Read or Glob (not test)
- Content search → Grep (not grep via Bash)
- Reading files → Read (not cat)
- Writing files → Write (not echo >)
- Editing files → Edit (not sed/awk)
- See diagnostic-patterns skill for complete patterns

**Should I create a new document?**
- Check if context-relevant document exists → Use existing
- Only create with user approval → Ask first

**Should I add this dependency?**
- ALWAYS get user approval → Ask first

## Usage

### In Agents

```markdown
### Step 0: Load Development Guidelines

```
Skill: plan-marshall:general-development-rules
```

This loads core principles for when to ask users, research requirements, and proper tool usage.
```

### In Commands

Commands should reference this skill when they need to enforce general development principles across their workflow.

## Integration

### With plan-marshall Bundle

**Agents:**
- **research-best-practices** - Used for researching current best practices

**Skills:**
- **diagnostic-patterns** - Detailed tool usage patterns
- Works with other utility command skills

**Commands:**
- All commands benefit from following these principles
- Commands delegate research to research-best-practices agent

### With Other Bundles

This skill provides cross-cutting principles useful for:
- pm-dev-java agents (implementation patterns)
- planning commands (when to ask users)
- pm-plugin-development (creating new components)
- Any development work in CUI ecosystem

## Core Principles Summary

### 1. User Interaction
**Principle:** If in doubt, ask the user.
**When:** Uncertain about requirements, approach, or interpretation.

### 2. Research Best Practices
**Principle:** Always research topics using research-best-practices agent.
**When:** Need current best practices for technologies/frameworks.
**Goal:** Find latest best practices, not outdated knowledge.

### 3. Proper Tool Usage
**Principle:** Use Read, Write, Edit, Glob, Grep (not cat, tail, find, test, etc.).
**When:** Performing file operations or content searches.
**Details:** See diagnostic-patterns skill for complete patterns.

### 4. Document Management
**Principle:** Don't proliferate documents; use existing context-relevant documents.
**When:** Creating new documentation or files.
**Requirement:** User approval before creating new documents.

### 5. Dependency Management
**Principle:** Never add dependencies without user approval.
**When:** Adding libraries, frameworks, or external dependencies.
**Requirement:** Always ask user first.

## Examples

### Example 1: Uncertain About Approach

```markdown
Following general-development-rules principle: "If in doubt, ask the user."

I have two potential approaches for implementing {feature}:
1. Approach A: {description}
2. Approach B: {description}

Which approach would you prefer?
```

### Example 2: Researching Best Practices

```markdown
Following general-development-rules: Research current best practices.

Launching research-best-practices agent to find latest best practices for {technology}.

Task:
  subagent_type: plan-marshall:research-best-practices
  prompt: Research best practices for {technology/framework}
```

### Example 3: Proper Tool Usage

```markdown
Following general-development-rules: Use proper tools for file operations.

Using Glob for file discovery (not find or ls):
Glob: pattern="**/*.java", path="src/main/java"

Using Read for checking file existence (not test):
Read: file_path="path/to/file.java"
(Handle error gracefully if file doesn't exist)
```

## Bundle

Part of the **plan-marshall** bundle - Utility commands and agents for CUI development.

## See Also

- research-best-practices agent - Comprehensive web research for current best practices
- diagnostic-patterns skill - Detailed tool usage patterns for non-prompting operations
- planning bundle - Development workflow integration
- pm-plugin-development bundle - Creating agents and commands following these principles
