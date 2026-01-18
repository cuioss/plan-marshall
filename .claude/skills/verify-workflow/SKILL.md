---
name: verify-workflow
description: Verify workflow outputs using hybrid script + LLM assessment
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Verify Workflow Skill

Verifies plan-marshall workflow outputs (solution_outline.md, references.toon, TASK-*.toon) using hybrid script + LLM-as-judge assessment.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `subcommand` | Yes | One of: `test`, `verify`, `create`, `list` |
| `--test-id` | test/verify/create | Test case identifier (kebab-case) |
| `--plan-id` | verify only | Existing plan to verify |

## Usage Examples

```bash
/verify-workflow test --test-id migrate-json-to-toon
/verify-workflow verify --test-id migrate-json-to-toon --plan-id my-plan
/verify-workflow create --test-id my-new-test
/verify-workflow list
```

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
Read: workflows/test-and-verify.md
```
Execute the **test** workflow section.

### verify
Verify existing plan (requires `--plan-id`).
```
Read: workflows/test-and-verify.md
```
Execute the **verify** workflow section.

### create
Create new test case interactively.
```
Read: workflows/create-test-case.md
```

### list
List available test cases.
```
Read: workflows/list-test-cases.md
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

### verify-structure.py
Structural verification via manage-* tool interfaces.

**Input**: `--plan-id`, `--test-case`, `--output`
**Output**: TOON file with structural check results

```bash
python3 scripts/verify-structure.py \
  --plan-id {plan_id} \
  --test-case workflow-verification/test-cases/{test-id} \
  --output .plan/temp/verify-{test-id}-structure.toon
```

### collect-artifacts.py
Artifact collection via manage-* tool interfaces.

**Input**: `--plan-id`, `--output`
**Output**: Directory with collected artifacts (solution_outline.md, config.toon, etc.)

```bash
python3 scripts/collect-artifacts.py \
  --plan-id {plan_id} \
  --output .plan/temp/verify-{test-id}-artifacts/
```
