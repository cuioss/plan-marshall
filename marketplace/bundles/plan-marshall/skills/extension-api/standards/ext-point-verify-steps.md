# Extension Point: Verify Steps

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_verify_steps()` | **Implementations**: 0 | **Status**: Placeholder

## Overview

Verify steps extensions declare domain-specific verification agents that run after implementation tasks complete. Steps are appended to the flat `steps` list in `plan.phase-5-execute.steps` and executed as holistic verification tasks.

## Implementor Requirements

### Interface Contract

Each verify step skill receives `--plan-id` and `--iteration` (current verification iteration, 1-based). Retry logic is managed by the task runner (Step 9 triage loop), not by the step itself.

**Return Contract** (required TOON output):

```toon
status: passed|failed
message: "Human-readable summary"

# Optional — only when status: failed
findings[N]{file,line,message,severity}:
src/Foo.java,42,Unused import,warning
```

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_verify_steps(self) -> list[dict]:
        return [
            {
                'name': 'my-bundle:my-verify-step',
                'skill': 'my-bundle:my-verify-step',
                'description': 'Custom domain verification',
            },
        ]
```

## Runtime Invocation Contract

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | str | Yes | Plan identifier |
| `iteration` | int | Yes | Current verification iteration (1-based) |

### Pre-Conditions

- Plan has completed all implementation tasks
- Steps registered in `marshal.json` under `plan.phase-5-execute.steps`
- Built-in steps (`default:quality_check`, `default:build_verify`) execute first

### Post-Conditions

- Verification result with pass/fail status
- Findings logged if failures detected
- Failed findings triaged via domain triage extension (Step 9 of phase-5-execute)

## Hook API

### Python API

```python
def provides_verify_steps(self) -> list[dict]:
    """Return domain-specific verification steps.

    Each step dict contains:
        - name: Fully-qualified skill reference (e.g., 'my-bundle:my-verify-step')
        - skill: Same as name (the fully-qualified skill reference)
        - description: Human-readable description for wizard presentation

    Default: []
    """
```

### Return Structure

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Fully-qualified skill reference (`bundle:skill`) — used directly in steps list |
| `skill` | str | Same as name |
| `description` | str | Human-readable description for `/marshall-steward` wizard |

## Storage in marshal.json

Extension steps are appended to the flat `plan.phase-5-execute.steps` list after built-in steps:

```json
{
  "plan": {
    "phase-5-execute": {
      "steps": [
        "default:quality_check",
        "default:build_verify",
        "my-bundle:my-verify-step"
      ]
    }
  }
}
```

**Path**: `plan.phase-5-execute.steps`

Built-in steps are always first. Extension steps follow in discovery order.

## Resolution

```bash
# Add a verify step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute add-step --step my-bundle:my-verify-step

# Remove a verify step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute remove-step --step my-bundle:my-verify-step

# Replace entire steps list
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps default:quality_check,default:build_verify

# List all available verify steps (built-in + extensions)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```

## Current Implementations

No bundles currently provide verification steps. Coverage verification is handled by the built-in `default:coverage_check` step, not by an extension.
