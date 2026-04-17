# Extension Point: Finalize Steps

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_finalize_steps()` | **Implementations**: 0 | **Status**: Placeholder

## Overview

Finalize steps extensions declare domain-specific steps that execute during the phase-6-finalize pipeline. Steps are discovered by marshall-steward and presented to the user for selection. Selected steps run in the configured order during plan finalization.

## Implementor Requirements

### Interface Contract

Each finalize step skill receives:

| Parameter | Description |
|-----------|-------------|
| `--plan-id` | The plan being finalized |
| `--iteration` | Current finalize iteration (1-based) |

The step skill can access plan context via manage-* scripts.

**Return Contract** (required TOON output):

```toon
status: passed|failed
message: "Human-readable summary"
```

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_finalize_steps(self) -> list[dict]:
        return [
            {
                'name': 'pm-dev-java:java-post-pr',
                'skill': 'pm-dev-java:java-post-pr',
                'description': 'Java post-PR validation and artifact publishing',
                'order': 500,
            },
        ]
```

> **Note**: `order` is NOT enforced at runtime. `marshall-steward` sorts the `steps` list by `order` when writing to `marshal.json`; phase-6-finalize iterates the list as written and does not re-sort or validate the ordering.

## Runtime Invocation Contract

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | str | Yes | Plan being finalized |
| `iteration` | int | Yes | Current finalize iteration (1-based) |

### Pre-Conditions

- Plan has passed verification (phase-5-execute complete)
- Steps registered in `marshal.json` under `plan.phase-6-finalize.steps`
- User selected steps during `/marshall-steward` configuration

### Post-Conditions

- Domain-specific finalization complete
- Step reports success/failure via TOON return contract
- Findings logged if failures detected

## Hook API

### Python API

```python
def provides_finalize_steps(self) -> list[dict]:
    """Return domain-specific finalize steps.

    Each step dict contains:
        - name: str — Fully-qualified skill notation (used as step reference)
        - skill: str — Same as name (fully-qualified skill reference)
        - description: str — Human-readable description for wizard presentation
        - order: int — Sort key used by marshall-steward when writing the
          steps list; steps with identical order prompt the user for
          disambiguation. Not enforced at runtime.

    Default: []
    """
```

### Return Structure

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Fully-qualified skill notation — used as step reference in `steps` list |
| `skill` | str | Same as `name` (the skill to invoke) |
| `description` | str | Human-readable description for `/marshall-steward` wizard |
| `order` | int | Sort key used by marshall-steward when writing the steps list; steps with identical order prompt the user |

## Storage in marshal.json

Extension-contributed steps are added to the ordered `steps` list:

```json
{
  "plan": {
    "phase-6-finalize": {
      "steps": [
        "default:commit_push",
        "default:create_pr",
        "pm-dev-java:java-post-pr",
        "default:branch_cleanup",
        "default:archive"
      ]
    }
  }
}
```

**Path**: `plan.phase-6-finalize.steps`

The step reference is the fully-qualified skill notation. Position determines execution order.

## Current Implementations

No bundles currently provide finalize steps.
