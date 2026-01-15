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
        "2-outline": "pm-workflow:phase-2-outline",
        "3-plan": "pm-workflow:phase-3-plan",
        "4-execute": "pm-workflow:phase-4-execute",
        "5-finalize": "pm-workflow:phase-5-finalize"
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
      "testing": {
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
      "compatibility": "deprecations",
      "commit_strategy": "phase-specific",
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

Skill configuration per domain using the 5-phase model.

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
        "2-outline": "pm-workflow:phase-2-outline",
        "3-plan": "pm-workflow:phase-3-plan",
        "4-execute": "pm-workflow:phase-4-execute",
        "5-finalize": "pm-workflow:phase-5-finalize"
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
      "testing": { "defaults": [], "optionals": [] },
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
| `testing` | execute | Test code development |
| `quality` | finalize | Documentation and verification |

### Extension Types

Extensions provide domain-specific behavior without replacing workflow skills:

| Type | Phase | Description |
|------|-------|-------------|
| `outline` | outline | Domain patterns and deliverable identification |
| `triage` | finalize | Finding decision logic (fix/suppress/accept) |

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
      "compatibility": "deprecations",
      "commit_strategy": "phase-specific",
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
| `compatibility` | string | "breaking" | deprecations, breaking |
| `commit_strategy` | string | "phase-specific" | fine-granular, phase-specific, complete |
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

## Default Values

Default values are defined in:

```
plan-marshall/skills/manage-plan-marshall-config/scripts/config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
