# Data Model

JSON structure and field definitions for project configuration.

## File Location

`.plan/marshal.json`

## Complete Structure

```json
{
  "ci": {
    "repo_url": "https://github.com/org/repo",
    "provider": "github",
    "detected_at": "2025-01-15T10:30:00Z",
    "sonar_project": null
  },
  "plan": {
    "phase-1-init": {
      "branch_strategy": "feature"
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking"
    },
    "phase-3-outline": {
      "plan_without_asking": false
    },
    "phase-4-plan": {
      "execute_without_asking": false
    },
    "phase-5-execute": {
      "commit_strategy": "per_deliverable",
      "verification_max_iterations": 5,
      "verification_1_quality_check": true,
      "verification_2_build_verify": true,
      "verification_domain_steps": {}

    },
    "phase-6-finalize": {
      "max_iterations": 3,
      "review_bot_buffer_seconds": 180,
      "steps": [
        "commit_push", "create_pr", "automated_review",
        "sonar_roundtrip", "lessons_capture",
        "branch_cleanup", "archive"
      ]
    }
  },
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:dev-general-practices"],
      "optionals": ["plan-marshall:dev-general-practices"],
      "execute_task_skills": {
        "implementation": "plan-marshall:execute-task",
        "module_testing": "plan-marshall:execute-task",
        "integration_testing": "plan-marshall:execute-task"
      }
    },
    "java": {
      "bundle": "pm-dev-java",
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  },
  "system": {
    "retention": {
      "logs_days": 1,
      "archived_plans_days": 5,
      "temp_on_maintenance": true
    }
  }
}
```

## Section: skill_domains

Skill configuration per domain. See [skill-domains.md](skill-domains.md) for complete domain structure, profiles, validation rules, and technical domain catalog. See [skill-domains-operations.md](skill-domains-operations.md) for resolution commands and usage patterns.

Key structural summary:
- **System domain**: Contains `defaults`, `optionals`, and `execute_task_skills`
- **Technical domains**: Reference a `bundle` and declare `workflow_skill_extensions` (outline, triage)
- **Profiles**: Loaded at runtime from `extension.py`, not stored in marshal.json

## Section: system

System-level infrastructure settings.

### Structure

```json
{
  "system": {
    "retention": {
      "logs_days": 1,
      "archived_plans_days": 5,
      "temp_on_maintenance": true
    }
  }
}
```

### Retention Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `logs_days` | int | 1 | Days to keep execution logs |
| `archived_plans_days` | int | 5 | Days to keep archived plans |
| `temp_on_maintenance` | bool | true | Clean temp on maintenance |

## Section: plan

Phase-specific configuration for the 6-phase workflow model. Each phase with configurable settings has its own sub-section.

> **Phase naming**: JSON keys use the `phase-{N}-{name}` prefix form (e.g., `phase-1-init`). The canonical phase name is `1-init` — see [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) for the standard phase list.

### phase-1-init

```json
{
  "plan": {
    "phase-1-init": {
      "branch_strategy": "feature"
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `branch_strategy` | string | "feature" | direct, feature |

### phase-2-refine

```json
{
  "plan": {
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking"
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `confidence_threshold` | int | 95 | Confidence threshold for refinement completion |
| `compatibility` | string | "breaking" | breaking, deprecation, smart_and_ask |

### phase-3-outline

```json
{
  "plan": {
    "phase-3-outline": {
      "plan_without_asking": false
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `plan_without_asking` | bool | false | Auto-proceed from outline to task creation without user review |

### phase-4-plan

```json
{
  "plan": {
    "phase-4-plan": {
      "execute_without_asking": false
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `execute_without_asking` | bool | false | Auto-continue to execute phase after task creation |

### phase-5-execute

Execute phase with integrated verification pipeline. Contains commit strategy, iteration limits, and a flat ordered `steps` list for verification.

```json
{
  "plan": {
    "phase-5-execute": {
      "commit_strategy": "per_deliverable",
      "finalize_without_asking": false,
      "verification_max_iterations": 5,
      "steps": [
        "default:quality_check",
        "default:build_verify",
        "default:coverage_check"
      ],
      "step_order_overrides": {
        "my-bundle:my-verify-step": 25
      }
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `commit_strategy` | string | "per_deliverable" | per_deliverable, per_plan, none |
| `finalize_without_asking` | bool | false | Auto-continue to finalize phase after execute completes |
| `verification_max_iterations` | int | 5 | Maximum verify-execute-verify loops |
| `step_order_overrides` | map | `{}` | Per-step integer override of the discovered `order` value — read by `set-steps` and `add-step` before falling back to the step's authoritative `order`. Managed via `set-step-order-override` / `remove-step-order-override`. |

#### Verification Steps

The `steps` list contains an ordered sequence of verification step references. Two types:

- **Built-in steps** (no colon): `quality_check` (run quality-gate), `build_verify` (run full test suite)
- **Extension steps** (colon notation): Fully-qualified skill references from domain bundles (e.g., `my-bundle:my-verify-step`)

Built-in steps are always first in the default list. Extension steps are appended by `skill-domains configure` from `provides_verify_steps()` in each domain's `extension.py`. See [extension-contract.md](../../extension-api/standards/extension-contract.md) for the complete contract.

Managed via:
- `plan phase-5-execute set-steps --steps quality_check,build_verify`
- `plan phase-5-execute add-step --step my-bundle:my-verify-step`
- `plan phase-5-execute remove-step --step quality_check`

### phase-6-finalize

Finalize pipeline with numbered boolean steps.

```json
{
  "plan": {
    "phase-6-finalize": {
      "max_iterations": 3,
      "review_bot_buffer_seconds": 180,
      "steps": [
        "default:commit-push", "default:create-pr", "default:automated-review",
        "default:sonar-roundtrip", "default:lessons-capture",
        "default:branch-cleanup", "default:record-metrics", "default:archive-plan"
      ],
      "step_order_overrides": {
        "pm-dev-java:java-post-pr": 75
      }
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_iterations` | int | 3 | Maximum finalize-verify-finalize loops |
| `review_bot_buffer_seconds` | int | 180 | Max seconds to wait after CI for new review-bot comments to arrive (used as `--timeout` for `pr wait-for-comments`; the polling subcommand exits as soon as a new comment is posted, so this is a ceiling, not a fixed delay) |
| `steps` | list | (see below) | Ordered list of step references to execute — persisted sorted ascending by each step's resolved `order` (override > authoritative source) |
| `step_order_overrides` | map | `{}` | Per-step integer override of the discovered `order` value — managed via `set-step-order-override` / `remove-step-order-override` |

Default steps: `commit_push`, `create_pr`, `automated_review`, `sonar_roundtrip`, `lessons_capture`, `branch_cleanup`, `archive`. Step types: built-in (plain name), project (`project:` prefix), skill (fully-qualified `bundle:skill`).

## Section: ci

CI provider configuration (project-level, shared via git).

### Structure

```json
{
  "ci": {
    "repo_url": "https://github.com/org/repo",
    "provider": "github",
    "detected_at": "2025-01-15T10:30:00Z",
    "sonar_project": "my-project-key"
  }
}
```

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_url` | string | No | - | Git remote origin URL |
| `provider` | string | Yes | - | CI provider: `github`, `gitlab`, `unknown` |
| `detected_at` | string | No | - | ISO timestamp of last detection |
| `sonar_project` | string | No | null | SonarQube/Cloud project key |

### Provider Values

| Value | CLI Tool | Description |
|-------|----------|-------------|
| `github` | `gh` | GitHub (github.com or enterprise) |
| `gitlab` | `glab` | GitLab (gitlab.com or self-hosted) |
| `unknown` | - | Could not detect provider |

### Note: Authenticated Tools

Tool availability is verified live via `plan-marshall:tools-integration-ci:ci_health verify-all` — it is not persisted, since tool/auth status varies per developer machine and is cheap to check on demand.

## Default Values

Default values are defined in:

```
plan-marshall/skills/manage-config/scripts/_config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
