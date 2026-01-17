---
name: verify-workflow
description: Verify workflow outputs using hybrid script + LLM assessment
---

# Verify Workflow Command

Verifies plan-marshall workflow outputs using hybrid script + LLM-as-judge assessment.

## PARAMETERS

| Parameter | Required | Description |
|-----------|----------|-------------|
| `subcommand` | Yes | One of: `test`, `verify`, `create`, `list` |
| `--test-id` | test/verify/create | Test case identifier (kebab-case) |
| `--plan-id` | verify only | Existing plan to verify |

## SUBCOMMANDS

| Command | Description |
|---------|-------------|
| `test` | Execute trigger from test-definition, then verify |
| `verify` | Verify existing plan (requires --plan-id) |
| `create` | Create new test case interactively |
| `list` | List available test cases |

## WORKFLOW

**Activate** the workflow-verify skill and pass the subcommand:

```
Skill: workflow-verify
```

The skill handles subcommand routing internally.

## USAGE EXAMPLES

```bash
/verify-workflow test --test-id migrate-json-to-toon
/verify-workflow verify --test-id migrate-json-to-toon --plan-id my-plan
/verify-workflow create --test-id my-new-test
/verify-workflow list
```

## RELATED

- `workflow-verify` skill - Orchestrates verification workflows
- `workflow-verification/` - Test case storage
