---
name: verify-workflow
description: Verify workflow outputs using hybrid script + LLM assessment
---

# Verify Workflow Command

Verifies plan-marshall workflow outputs (solution_outline.md, references.toon, tasks) are correct and complete using hybrid script + LLM-as-judge assessment.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "verify-workflow", bundle: "project-local"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- `subcommand` (required): One of: `create`, `run`, `list`
- `--test-id` (required for create/run): Test case identifier (kebab-case)

## SUBCOMMAND ROUTING

Parse the user input to determine which subcommand to execute:

- **"create"** or input contains "create" → Execute Create Workflow
- **"run"** or input contains "run" or "verify" → Execute Run Workflow
- **"list"** or input contains "list" or "show" → Execute List Workflow

## WORKFLOW

### Subcommand: create

Interactive test case creation wizard.

**Activate** the workflow-verify skill and execute the **Create Test Case** workflow:

```
Skill: workflow-verify
```

Execute the "Create Test Case" workflow with the provided `--test-id`.

### Subcommand: run

Execute verification against a test case.

**Activate** the workflow-verify skill and execute the **Run Verification** workflow:

```
Skill: workflow-verify
```

Execute the "Run Verification" workflow with the provided `--test-id`.

### Subcommand: list

List available test cases.

**Activate** the workflow-verify skill and execute the **List Test Cases** workflow:

```
Skill: workflow-verify
```

Execute the "List Test Cases" workflow.

## USAGE EXAMPLES

```
/verify-workflow create --test-id migrate-json-to-toon
/verify-workflow run --test-id migrate-json-to-toon
/verify-workflow list
```

## RELATED

- `workflow-verify` skill - Orchestrates verification workflows
- `workflow-verification/` - Test case and results storage
