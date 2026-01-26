# Data Model

JSON structure and field definitions for project configuration.

## File Location

`.plan/marshal.json`

## Complete Structure

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:ref-development-standards"],
      "optionals": ["plan-marshall:ref-development-standards"],
      "workflow_skills": {
        "1-init": "pm-workflow:phase-1-init",
        "2-refine": "pm-workflow:phase-2-refine",
        "3-outline": "pm-workflow:phase-3-outline",
        "4-plan": "pm-workflow:phase-4-plan",
        "5-execute": "pm-workflow:phase-5-execute",
        "6-verify": "pm-workflow:phase-6-verify",
        "7-finalize": "pm-workflow:phase-7-finalize"
      }
    },
    "java": {
      "workflow_skill_extensions": {
        "outline": "pm-dev-java:java-outline-ext",
        "triage": "pm-dev-java:ext-triage-java"
      },
      "core": {
        "defaults": ["pm-dev-java:java-core"],
        "optionals": ["pm-dev-java:java-null-safety", "pm-dev-java:java-lombok"]
      },
      "implementation": {
        "defaults": [],
        "optionals": ["pm-dev-java:java-cdi", "pm-dev-java:java-maintenance"]
      },
      "module_testing": {
        "defaults": ["pm-dev-java:junit-core"],
        "optionals": []
      },
      "integration_testing": {
        "defaults": ["pm-dev-java:junit-core"],
        "optionals": ["pm-dev-java:junit-integration"]
      },
      "quality": {
        "defaults": ["pm-dev-java:javadoc"],
        "optionals": []
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
  },
  "plan": {
    "defaults": {
      "compatibility": "breaking",
      "commit_strategy": "per_deliverable",
      "create_pr": false,
      "verification_required": true,
      "branch_strategy": "direct"
    },
    "finalize": {
      "commit": true
    }
  },
  "ci": {
    "enabled": true,
    "repo_url": "https://github.com/org/repo",
    "provider": "github",
    "sonar_project": null
  }
}
```

## Section: skill_domains

Skill configuration per domain using the 7-phase model.

### System Domain Structure

The `system` domain contains workflow skills and base skills applied globally.

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["bundle:skill", ...],
      "optionals": ["bundle:skill", ...],
      "workflow_skills": {
        "1-init": "pm-workflow:phase-1-init",
        "2-refine": "pm-workflow:phase-2-refine",
        "3-outline": "pm-workflow:phase-3-outline",
        "4-plan": "pm-workflow:phase-4-plan",
        "5-execute": "pm-workflow:phase-5-execute",
        "6-verify": "pm-workflow:phase-6-verify",
        "7-finalize": "pm-workflow:phase-7-finalize"
      }
    }
  }
}
```

### Technical Domain Structure (Profile-Based)

Technical domains (java, javascript, etc.) use profile-based organization:

```json
{
  "skill_domains": {
    "{domain}": {
      "workflow_skill_extensions": {
        "outline": "bundle:extension-skill",
        "triage": "bundle:triage-skill"
      },
      "core": {
        "defaults": ["bundle:skill", ...],
        "optionals": ["bundle:skill", ...]
      },
      "implementation": { "defaults": [], "optionals": [] },
      "module_testing": { "defaults": [], "optionals": [] },
      "integration_testing": { "defaults": [], "optionals": [] },
      "quality": { "defaults": [], "optionals": [] }
    }
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `workflow_skills` | object | System domain only - maps phases to workflow skills |
| `workflow_skill_extensions` | object | Domain-specific extensions (outline, triage) |
| `defaults` | array | Skills always loaded |
| `optionals` | array | Skills available for selection |

### Profiles

Profiles determine which skills to load based on task context:

| Profile | Phase | Description |
|---------|-------|-------------|
| `implementation` | execute | Production code development |
| `module_testing` | execute | Unit/module test development |
| `integration_testing` | execute | Integration test development |
| `quality` | verify | Documentation and verification |

### Extension Types

Extensions provide domain-specific behavior without replacing workflow skills:

| Type | Phase | Description |
|------|-------|-------------|
| `outline` | outline | Domain patterns and deliverable identification |
| `triage` | verify | Finding decision logic (fix/suppress/accept) |

### Capabilities (Domain Resolution)

Each domain can define capabilities for `${domain}` placeholder resolution:

```json
{
  "skill_domains": {
    "java": {
      "capabilities": {
        "quality-gate": "pm-dev-java:java-quality-agent",
        "build-verify": "pm-dev-java:java-verify-agent",
        "impl-verify": "pm-dev-java:java-verify-agent",
        "test-verify": "pm-dev-java:java-coverage-agent",
        "triage": "pm-dev-java:ext-triage-java"
      }
    },
    "javascript": {
      "capabilities": {
        "quality-gate": null,
        "build-verify": null,
        "triage": "pm-dev-frontend:ext-triage-js"
      }
    },
    "plan-marshall-plugin-dev": {
      "capabilities": {
        "triage": "pm-plugin-development:ext-triage-plugin"
      }
    },
    "documentation": {
      "capabilities": {
        "triage": "pm-documents:ext-triage-docs"
      }
    }
  }
}
```

When a step specifies `skill: "${domain}:quality-gate"` and `config.toon.domains: ["java"]`, the resolved skill is `pm-dev-java:java-quality-agent`.

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

Plan-related configuration including execution defaults and finalize behavior.

### Structure

```json
{
  "plan": {
    "defaults": {
      "compatibility": "breaking",
      "commit_strategy": "per_deliverable",
      "create_pr": false,
      "verification_required": true,
      "branch_strategy": "direct"
    },
    "finalize": {
      "commit": true
    }
  }
}
```

### Defaults Fields

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `compatibility` | string | "breaking" | breaking, deprecation, smart_and_ask |
| `commit_strategy` | string | "per_deliverable" | per_deliverable, per_plan, none |
| `create_pr` | bool | false | true, false |
| `verification_required` | bool | true | true, false |
| `branch_strategy` | string | "direct" | direct, feature |

### Finalize Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `commit` | bool | true | Commit changes after finalize phase |

Note: `create_pr` is in `defaults` as it applies to multiple phases. The finalize workflow skill reads both `plan.defaults.create_pr` and `plan.finalize.commit`.

## Section: ci

CI provider configuration (project-level, shared via git).

### Structure

```json
{
  "ci": {
    "enabled": true,
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
| `enabled` | bool | No | true | Whether to wait for CI checks during finalize |
| `repo_url` | string | No | - | Git remote origin URL |
| `provider` | string | Yes | - | CI provider: `github`, `gitlab`, `unknown` |
| `detected_at` | string | No | - | ISO timestamp of last detection |
| `sonar_project` | string | No | null | SonarQube/Cloud project key (if Sonar analysis is configured) |

### Provider Values

| Value | CLI Tool | Description |
|-------|----------|-------------|
| `github` | `gh` | GitHub (github.com or enterprise) |
| `gitlab` | `glab` | GitLab (gitlab.com or self-hosted) |
| `unknown` | - | Could not detect provider |

### Note: Authenticated Tools

Tool availability (`authenticated_tools`) is stored in `run-configuration.json` (local, not shared via git) since it varies per developer machine. See run-config skill for the `ci` section schema.

## Section: verification

**Optional**: These sections override the hardcoded defaults in the phase skills. When absent, phase-6-verify and phase-7-finalize use their built-in pipeline.

Step pipeline configuration for the 6-verify phase.

### Structure

```json
{
  "verification": {
    "max_iterations": 5,
    "steps": [
      { "name": "quality_check", "skill": "${domain}:quality-gate", "type": "build" },
      { "name": "build_verify", "skill": "${domain}:build-verify", "type": "build" },
      { "name": "technical_impl", "skill": "${domain}:impl-verify", "type": "agent" },
      { "name": "technical_test", "skill": "${domain}:test-verify", "type": "agent" },
      { "name": "doc_sync", "skill": "pm-documents:doc-verify", "type": "advisory" },
      { "name": "formal_spec", "skill": "pm-requirements:spec-verify", "type": "advisory" }
    ]
  }
}
```

### Step Types

| Type | Purpose | Can Block | Can Loop Back |
|------|---------|-----------|---------------|
| `build` | Build/compile commands | Yes | Yes |
| `agent` | Verification agents | Yes | Yes |
| `advisory` | Info capture | No | No |

### Domain Placeholder

The `${domain}` placeholder is resolved at runtime using capabilities from `skill_domains.{domain}.capabilities`.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_iterations` | int | 5 | Maximum verify→execute→verify loops |
| `steps` | array | - | Ordered step definitions |
| `steps[].name` | string | - | Step identifier |
| `steps[].skill` | string | - | Skill to invoke (supports `${domain}` placeholder) |
| `steps[].type` | string | - | Step type: `build`, `agent`, `advisory` |

## Section: finalize

**Optional**: These sections override the hardcoded defaults in the phase skills. When absent, phase-7-finalize uses its built-in pipeline.

Step pipeline configuration for the 7-finalize phase.

### Structure

```json
{
  "finalize": {
    "max_iterations": 3,
    "steps": [
      { "name": "commit_push", "skill": "pm-workflow:workflow-integration-git", "type": "action" },
      { "name": "create_pr", "skill": "pm-workflow:workflow-integration-git", "type": "action" },
      { "name": "automated_review", "skill": "pm-workflow:workflow-integration-ci", "type": "api" },
      { "name": "sonar_roundtrip", "skill": "pm-workflow:workflow-integration-sonar", "type": "api" },
      { "name": "knowledge_capture", "skill": "plan-marshall:manage-memories", "type": "advisory" },
      { "name": "lessons_capture", "skill": "plan-marshall:manage-lessons", "type": "advisory" }
    ]
  }
}
```

### Step Types

| Type | Purpose | Can Block | Can Loop Back |
|------|---------|-----------|---------------|
| `action` | Binary success/fail | Yes | No |
| `api` | External APIs (CI, Sonar) | Yes | Yes |
| `advisory` | Info capture | No | No |

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_iterations` | int | 3 | Maximum finalize→verify→finalize loops |
| `steps` | array | - | Ordered step definitions |

## Default Values

Default values are defined in:

```
plan-marshall/skills/manage-plan-marshall-config/scripts/_config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
