# Data Model

JSON structure and field definitions for project configuration.

## File Location

`.plan/marshal.json`

## Complete Structure

```json
{
  "skill_domains": {
    "system": {
      "defaults": ["plan-marshall:general-development-rules"],
      "optionals": ["plan-marshall:diagnostic-patterns"],
      "workflow_skills": {
        "init": "pm-workflow:plan-init",
        "outline": "pm-workflow:solution-outline",
        "plan": "pm-workflow:task-plan",
        "execute": "pm-workflow:task-execute",
        "finalize": "pm-workflow:plan-finalize"
      }
    },
    "java": {
      "workflow_skill_extensions": {
        "outline": "pm-dev-java:java-outline-ext",
        "triage": "pm-dev-java:java-triage"
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
    },
    "javascript": {
      "workflow_skill_extensions": {
        "outline": "pm-dev-frontend:js-outline-ext",
        "triage": "pm-dev-frontend:javascript-triage"
      },
      "core": {
        "defaults": ["pm-dev-frontend:cui-javascript"],
        "optionals": ["pm-dev-frontend:cui-jsdoc", "pm-dev-frontend:cui-javascript-project"]
      },
      "implementation": {
        "defaults": [],
        "optionals": ["pm-dev-frontend:cui-javascript-maintenance", "pm-dev-frontend:cui-javascript-linting"]
      },
      "testing": {
        "defaults": ["pm-dev-frontend:cui-javascript-unit-testing"],
        "optionals": ["pm-dev-frontend:cui-cypress"]
      },
      "quality": {
        "defaults": [],
        "optionals": []
      }
    },
    "plan-marshall-plugin-dev": {
      "workflow_skill_extensions": {
        "triage": "pm-plugin-development:plugin-triage"
      },
      "core": {
        "defaults": ["pm-plugin-development:plugin-architecture"],
        "optionals": ["pm-plugin-development:plugin-script-architecture"]
      },
      "implementation": {
        "defaults": [],
        "optionals": ["pm-plugin-development:plugin-create", "pm-plugin-development:plugin-maintain"]
      },
      "testing": {
        "defaults": [],
        "optionals": []
      },
      "quality": {
        "defaults": ["pm-plugin-development:plugin-doctor"],
        "optionals": []
      }
    }
  },
  "modules": {
    "default": {
      "path": ".",
      "type": "pom",
      "domains": ["java-core", "java-implementation"],
      "build_systems": ["maven"],
      "detected_profiles": [
        {"id": "pre-commit", "canonical": "quality-gate", "activation": {"type": "command-line"}}
      ],
      "commands": {
        "quality-gate": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify -Ppre-commit\"",
        "install": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean install\""
      }
    },
    "my-module": {
      "path": "my-module",
      "type": "jar",
      "domains": ["java-core", "java-implementation"],
      "build_systems": ["maven"],
      "commands": {
        "module-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean test\" --module my-module",
        "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify\" --module my-module",
        "quality-gate": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify -Ppre-commit\" --module my-module"
      }
    },
    "my-hybrid-ui": {
      "path": "my-hybrid-ui",
      "type": "war",
      "domains": ["java-core", "java-implementation", "javascript-core", "javascript-implementation"],
      "build_systems": ["maven", "npm"],
      "commands": {
        "module-tests": {
          "maven": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean test\" --module my-hybrid-ui",
          "npm": "python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm execute --command \"run test\" --module my-hybrid-ui"
        },
        "quality-gate": {
          "maven": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify -Ppre-commit\" --module my-hybrid-ui",
          "npm": "python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm execute --command \"run lint && npm run format:check\" --module my-hybrid-ui"
        }
      }
    }
  },
  "build_systems": [
    {
      "system": "maven",
      "skill": "pm-dev-java:plan-marshall-plugin"
    },
    {
      "system": "gradle",
      "skill": "pm-dev-java:plan-marshall-plugin"
    },
    {
      "system": "npm",
      "skill": "pm-dev-java:plan-marshall-plugin"
    }
  ],
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
        "init": "pm-workflow:plan-init",
        "outline": "pm-workflow:solution-outline",
        "plan": "pm-workflow:task-plan",
        "execute": "pm-workflow:task-execute",
        "finalize": "pm-workflow:plan-finalize"
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

## Section: modules

Project module configuration with type, domain, build system, and canonical command mappings.

### Structure

```json
{
  "modules": {
    "{module-name}": {
      "path": "relative/path",
      "type": "jar|pom|war|quarkus|npm",
      "domains": ["domain1", "domain2"],
      "build_systems": ["system1", "system2"],
      "detected_profiles": [
        {"id": "profile-id", "canonical": "canonical-name", "activation": {"type": "command-line|property"}}
      ],
      "commands": {
        "{canonical-name}": "python3 .plan/execute-script.py {domain}:plan-marshall-plugin:{system} run --targets \"{goals}\""
      }
    }
  }
}
```

### Example (Single Build System)

```json
{
  "modules": {
    "my-module": {
      "path": "my-module",
      "type": "jar",
      "domains": ["java-core", "java-implementation"],
      "build_systems": ["maven"],
      "detected_profiles": [
        {"id": "integration-tests", "canonical": "integration-tests", "activation": {"type": "command-line"}},
        {"id": "coverage", "canonical": "coverage", "activation": {"type": "command-line"}}
      ],
      "commands": {
        "module-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean test\" --module my-module",
        "integration-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify -Pintegration-tests\" --module my-module",
        "coverage": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify -Pcoverage\" --module my-module",
        "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify\" --module my-module",
        "quality-gate": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify -Ppre-commit\" --module my-module"
      }
    }
  }
}
```

### Example (Hybrid Module - Maven + npm)

For modules with multiple build systems, commands use nested format:

```json
{
  "modules": {
    "my-hybrid-ui": {
      "path": "my-hybrid-ui",
      "type": "war",
      "domains": ["java-core", "javascript-core"],
      "build_systems": ["maven", "npm"],
      "commands": {
        "module-tests": {
          "maven": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean test\" --module my-hybrid-ui",
          "npm": "python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm execute --command \"run test\" --module my-hybrid-ui"
        },
        "quality-gate": {
          "maven": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets \"clean verify -Ppre-commit\" --module my-hybrid-ui",
          "npm": "python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm execute --command \"run lint && npm run format:check\" --module my-hybrid-ui"
        }
      }
    }
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | Relative path from project root |
| `type` | string | Yes | Module type: `pom`, `jar`, `war`, `quarkus`, `npm` |
| `domains` | array | Yes | Skill domains for this module |
| `build_systems` | array | Yes | Available build systems (for detection info) |
| `detected_profiles` | array | No | Maven/Gradle profiles with canonical mappings |
| `commands` | object | Yes | Canonical name to command string (or nested dict for hybrid) |

### Module Types

| Type | Description | Applicable Commands |
|------|-------------|---------------------|
| `pom` | Parent/BOM module | install, quality-gate (no tests) |
| `jar` | Library module | All canonical commands |
| `war` | Web application | All canonical commands |
| `quarkus` | Quarkus application | All canonical commands + native |
| `npm` | npm project | npm-specific commands only |

### Canonical Command Names

Commands use a fixed vocabulary for programmatic lookup:

| Canonical | Phase | Description |
|-----------|-------|-------------|
| `compile` | build | Compile production code |
| `test-compile` | build | Compile test code |
| `module-tests` | test | Unit tests for the module |
| `integration-tests` | test | Integration/E2E tests |
| `coverage` | test | Test coverage reports |
| `performance` | test | Benchmark/performance tests |
| `quality-gate` | quality | Pre-commit checks (lint, format, static analysis) |
| `verify` | verify | Full build verification |
| `install` | deploy | Install to local repository |
| `package` | deploy | Create distributable package |

### Command Resolution (Static Routing)

Commands are stored as **full executable strings** - no runtime routing needed:

1. Get command from `modules.{name}.commands.{canonical}`
2. For hybrid modules, specify build system: `modules.{name}.commands.{canonical}.{system}`
3. Execute directly with `eval "$COMMAND"`
4. If module doesn't have the canonical, fall back to `modules.default.commands.{canonical}`

### Lookup API

Use the build_env script for programmatic command lookup:

```bash
# Single build system module
python3 .plan/execute-script.py plan-marshall:extension-api:build_env lookup \
  --canonical "module-tests" --module "my-module"

# Hybrid module with build system filter
python3 .plan/execute-script.py plan-marshall:extension-api:build_env lookup \
  --canonical "module-tests" --module "my-hybrid-ui" --build-system "npm"
```

### Static Routing Benefits

- **Transparency**: Config shows exactly what runs
- **Customization**: User can edit marshal.json to customize any command
- **No runtime logic**: Command already contains correct script path
- **Single mental model**: Same pattern as CI commands
- **Programmatic lookup**: Agents use canonical names for consistent API

## Section: build_systems

Build system detection and skill reference. Used by wizard for initial setup.

### Structure

```json
{
  "build_systems": [
    {
      "system": "maven",
      "skill": "pm-dev-java:plan-marshall-plugin"
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `system` | string | Build system identifier (maven, gradle, npm) |
| `skill` | string | Skill for executing builds |

### Role in Static Routing

The `build_systems` section serves as:
- **Detection reference**: Wizard uses this to map detected systems to skills
- **Skill lookup**: Agents can look up which skill handles which system

Command execution uses `modules.{name}.commands.{label}` directly - no runtime routing through build_systems is needed.

### Supported Systems

| System | Skill | Detection Files |
|--------|-------|-----------------|
| `maven` | `pm-dev-java:plan-marshall-plugin` | `pom.xml` |
| `gradle` | `pm-dev-java:plan-marshall-plugin` | `build.gradle`, `build.gradle.kts` |
| `npm` | `pm-dev-frontend:plan-marshall-plugin` | `package.json` |

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
plan-marshall/skills/plan-marshall-config/scripts/config_defaults.py
```

The `get_default_config()` function returns the complete default configuration used during `init`.
