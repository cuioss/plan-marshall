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
      "branch_strategy": "direct"
    },
    "phase-2-refine": {
      "confidence_threshold": 95,
      "compatibility": "breaking"
    },
    "phase-5-execute": {
      "commit_strategy": "per_deliverable"
    },
    "phase-6-verify": {
      "max_iterations": 5,
      "1_quality_check": true,
      "2_build_verify": true,
      "domain_steps": {
        "java": {
          "1_technical_impl": "pm-dev-java:java-verify-agent",
          "2_technical_test": "pm-dev-java:java-coverage-agent"
        },
        "documentation": {
          "1_doc_sync": "pm-documents:doc-verify"
        }
      }
    },
    "phase-7-finalize": {
      "max_iterations": 3,
      "1_commit_push": true,
      "2_create_pr": true,
      "3_automated_review": true,
      "4_sonar_roundtrip": true,
      "5_knowledge_capture": true,
      "6_lessons_capture": true
    }
  },
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:ref-development-standards"],
      "optionals": ["plan-marshall:ref-development-standards"],
      "task_executors": {
        "implementation": "pm-workflow:task-implementation",
        "module_testing": "pm-workflow:task-module_testing",
        "integration_testing": "pm-workflow:task-integration_testing"
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
      "memory_days": 5,
      "temp_on_maintenance": true
    }
  }
}
```

## Section: skill_domains

Skill configuration per domain.

### System Domain Structure

The `system` domain contains task executors and base skills applied globally.

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["bundle:skill", ...],
      "optionals": ["bundle:skill", ...],
      "task_executors": {
        "implementation": "pm-workflow:task-implementation",
        "module_testing": "pm-workflow:task-module_testing",
        "integration_testing": "pm-workflow:task-integration_testing"
      }
    }
  }
}
```

### Technical Domain Structure (Bundle-Based)

Technical domains (java, javascript, etc.) reference a bundle and declare workflow skill extensions. Profiles (core, implementation, module_testing, etc.) are loaded at runtime from `extension.py` in the bundle.

```json
{
  "skill_domains": {
    "{domain}": {
      "bundle": "pm-dev-java",
      "workflow_skill_extensions": {
        "outline": "bundle:extension-skill",
        "triage": "bundle:triage-skill"
      }
    }
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_executors` | object | System domain only - maps profiles to task executor skills |
| `bundle` | string | Technical domains - bundle providing this domain |
| `workflow_skill_extensions` | object | Domain-specific extensions (outline, triage) |
| `defaults` | array | Skills always loaded |
| `optionals` | array | Skills available for selection |

### Profiles

Profiles determine which skills to load based on task context. They are loaded from `extension.py` at runtime, not stored in marshal.json.

| Profile | Phase | Description |
|---------|-------|-------------|
| `implementation` | execute | Production code development |
| `module_testing` | execute | Unit/module test development |
| `integration_testing` | execute | Integration test development |
| `quality` | verify | Documentation and verification |

### Extension Types

Extensions provide domain-specific behavior:

| Type | Phase | Description |
|------|-------|-------------|
| `outline` | outline | Domain patterns and deliverable identification |
| `triage` | verify | Finding decision logic (fix/suppress/accept) |

## Section: system

System-level infrastructure settings.

### Structure

```json
{
  "system": {
    "retention": {
      "logs_days": 1,
      "archived_plans_days": 5,
      "memory_days": 5,
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
| `memory_days` | int | 5 | Days to keep memory entries |
| `temp_on_maintenance` | bool | true | Clean temp on maintenance |

## Section: plan

Phase-specific configuration for the 7-phase workflow model. Each phase with configurable settings has its own sub-section.

### phase-1-init

```json
{
  "plan": {
    "phase-1-init": {
      "branch_strategy": "direct"
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `branch_strategy` | string | "direct" | direct, feature |

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

### phase-5-execute

```json
{
  "plan": {
    "phase-5-execute": {
      "commit_strategy": "per_deliverable"
    }
  }
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `commit_strategy` | string | "per_deliverable" | per_deliverable, per_plan, none |

### phase-6-verify

Verification pipeline with generic boolean steps and domain-contributed agent steps.

```json
{
  "plan": {
    "phase-6-verify": {
      "max_iterations": 5,
      "1_quality_check": true,
      "2_build_verify": true,
      "domain_steps": {
        "java": {
          "1_technical_impl": "pm-dev-java:java-verify-agent",
          "2_technical_test": "pm-dev-java:java-coverage-agent"
        },
        "documentation": {
          "1_doc_sync": "pm-documents:doc-verify"
        }
      }
    }
  }
}
```

#### Generic Steps

Steps `1_quality_check` and `2_build_verify` are static booleans. They run canonical commands from `analyze-project-architecture`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_iterations` | int | 5 | Maximum verify-execute-verify loops |
| `1_quality_check` | bool | true | Run build quality gate |
| `2_build_verify` | bool | true | Run build verification |

#### Domain Steps

`domain_steps` contains per-domain verification steps with fully-qualified agent references. Each domain bundle declares its verification steps via `provides_verify_steps()` in `extension.py`.

- String value → invoke the agent reference
- `false` → skip the step

Domain steps are auto-populated by `skill-domains configure` and can be toggled via:
- `plan phase-6-verify set-domain-step --domain X --step Y --enabled false`
- `plan phase-6-verify set-domain-step-agent --domain X --step Y --agent bundle:agent`

### phase-7-finalize

Finalize pipeline with numbered boolean steps.

```json
{
  "plan": {
    "phase-7-finalize": {
      "max_iterations": 3,
      "1_commit_push": true,
      "2_create_pr": true,
      "3_automated_review": true,
      "4_sonar_roundtrip": true,
      "5_knowledge_capture": true,
      "6_lessons_capture": true
    }
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_iterations` | int | 3 | Maximum finalize-verify-finalize loops |
| `1_commit_push` | bool | true | Commit and push changes |
| `2_create_pr` | bool | true | Create pull request |
| `3_automated_review` | bool | true | CI automated review |
| `4_sonar_roundtrip` | bool | true | Sonar analysis roundtrip |
| `5_knowledge_capture` | bool | true | Capture learnings to memory |
| `6_lessons_capture` | bool | true | Record lessons learned |

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

Tool availability (`authenticated_tools`) is stored in `run-configuration.json` (local, not shared via git) since it varies per developer machine.

## Default Values

Default values are defined in:

```
plan-marshall/skills/manage-plan-marshall-config/scripts/_config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
