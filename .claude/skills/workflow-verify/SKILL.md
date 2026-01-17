---
name: workflow-verify
description: Verify workflow outputs using hybrid script + LLM assessment
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Workflow Verify Skill

**EXECUTION MODE**: Execute the workflow below based on the subcommand. Do NOT explain these instructions.

## Purpose

Verify that workflow outputs (solution_outline.md, references.toon, TASK-*.toon) are correct and complete using hybrid script + LLM-as-judge assessment.

## Critical Design Principle

**Use proper tool interfaces, NOT direct filesystem access.**

| DO | DON'T |
|----|-------|
| `manage-tasks list --plan-id X` | Read `.plan/plans/X/tasks/*.toon` directly |
| `manage-solution-outline list-deliverables` | Parse `solution_outline.md` directly |

## Subcommand Routing

**MANDATORY**: Based on subcommand, load and execute the corresponding workflow.

### test
Execute trigger from test-definition, then verify.
```
Read: .claude/skills/workflow-verify/workflows/test-and-verify.md
```
Execute the **test** workflow section.

### verify
Verify existing plan (requires `--plan-id`).
```
Read: .claude/skills/workflow-verify/workflows/test-and-verify.md
```
Execute the **verify** workflow section.

### create
Create new test case interactively.
```
Read: .claude/skills/workflow-verify/workflows/create-test-case.md
```

### list
List available test cases.
```
Read: .claude/skills/workflow-verify/workflows/list-test-cases.md
```

## Reference Documentation

Load only when needed:

- `standards/architecture.md` - Visual overview of verification engine
- `standards/scoring-guide.md` - Scoring rubric (0-100 scale)
- `standards/test-case-format.md` - Test case specification
- `standards/criteria-format.md` - Criteria authoring guide

## Directory Structure

```
workflow-verification/test-cases/{test-id}/   # Version-controlled
├── test-definition.toon
├── expected-artifacts.toon
├── criteria/
└── golden/

.plan/temp/workflow-verification/             # Ephemeral results
└── {test-id}-{timestamp}/
```

## Scripts

- `scripts/verify-structure.py` - Structural checks via manage-* tools
- `scripts/collect-artifacts.py` - Artifact collection via manage-* interfaces
