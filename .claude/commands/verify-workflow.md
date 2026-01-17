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

- `subcommand` (required): One of: `test`, `verify`, `create`, `list`
- `--test-id` (required for test/verify/create): Test case identifier (kebab-case)
- `--plan-id` (required for verify): Existing plan to verify

## SUBCOMMAND ROUTING

Parse the user input to determine which subcommand to execute:

- **"test"** → Execute trigger from test-definition, then verify (full automated)
- **"verify"** → Verify existing plan (requires --plan-id)
- **"create"** → Create new test case
- **"list"** → List available test cases

## WORKFLOW

### Subcommand: test

Execute the trigger command from test-definition, then verify the output.

**Activate** the workflow-verify skill:
```
Skill: workflow-verify
```

Execute the "Test Workflow" workflow with the provided `--test-id`.

### Subcommand: verify

Verify an existing plan against test case criteria (no execution).

**Activate** the workflow-verify skill:
```
Skill: workflow-verify
```

Execute the "Verify Plan" workflow with the provided `--test-id` and `--plan-id`.

### Subcommand: create

Interactive test case creation wizard.

**Activate** the workflow-verify skill:
```
Skill: workflow-verify
```

Execute the "Create Test Case" workflow with the provided `--test-id`.

### Subcommand: list

List available test cases.

**Activate** the workflow-verify skill:
```
Skill: workflow-verify
```

Execute the "List Test Cases" workflow.

## USAGE EXAMPLES

```
# Full automated test (execute trigger + verify)
/verify-workflow test --test-id migrate-json-to-toon

# Verify existing plan output
/verify-workflow verify --test-id migrate-json-to-toon --plan-id migrate-outputs-json-to-toon

# Create new test case
/verify-workflow create --test-id my-new-test

# List available test cases
/verify-workflow list
```

## RELATED

- `workflow-verify` skill - Orchestrates verification workflows
- `workflow-verification/` - Test case and results storage
