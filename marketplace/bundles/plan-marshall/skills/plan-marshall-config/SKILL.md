---
name: plan-marshall-config
description: Project-level infrastructure configuration for marshal.json
allowed-tools: Read, Write, Edit, Bash
---

# Plan-Marshall Config Skill

Manages project-level infrastructure configuration in `.plan/marshal.json`.

## What This Skill Provides

- **Skill Domains**: Implementation skill defaults and optionals per domain
- **Modules**: Project module configuration with domain/build-system mappings
- **Build Systems**: Build system detection and command configuration
- **System Settings**: Retention and cleanup configuration
- **Plan Defaults**: Default values for new plans

## When to Activate This Skill

Activate this skill when:
- Initializing project configuration (`/marshall-steward` wizard)
- Querying implementation skills for a domain
- Resolving build commands for a module
- Managing retention settings
- Configuring plan defaults

---

## Workflow: Initialize Configuration

**Pattern**: Script Automation

Initialize marshal.json with defaults and auto-detection.

### Step 1: Initialize

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config init
```

### Step 2: Detect Build Systems

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config build-systems detect
```

### Step 3: Detect Modules

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config modules detect
```

---

## Workflow: Query Skill Domains

**Pattern**: Read-Process-Write

Get implementation skills for a specific domain.

### Get Domain Defaults

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains get-defaults --domain java-core
```

**Output**:
```toon
status: success
domain: java-core
defaults[1]:
- pm-dev-java:java-core
```

### Get Domain Optionals

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains get-optionals --domain java-implementation
```

### Validate Skill in Domain

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  skill-domains validate --domain java-core --skill pm-dev-java:java-lombok
```

---

## Workflow: Query Module Configuration

**Pattern**: Read-Process-Write

Get module-specific configuration including domain and build system mappings.

### List All Modules

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  modules list
```

### Get Module Domains

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  modules get-domains --module my-module
```

### Get Build Command (Static Routing)

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  modules get-command --module my-module --label verify
```

**Output**:
```toon
status: success
module: my-module
label: verify
command: python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets "clean verify" --module my-module
source: module
```

Command resolution order:
1. Module-specific command (if defined in `modules.{name}.commands`)
2. Default module command (fallback to `modules.default.commands`)

### Set Build Command

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  modules set-command --module my-module --label verify \
  --command 'python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --targets "clean verify" --module my-module'
```

---

## Workflow: Query Build Systems

**Pattern**: Read-Process-Write

Get build system detection reference. Commands are resolved via `modules get-command`.

### List Build Systems

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  build-systems list
```

**Note**: Build commands are not stored in `build_systems` section. Use `modules get-command --module {module} --label {label}` to resolve executable commands.

---

## Workflow: System Settings

**Pattern**: Read-Process-Write

Manage system-level infrastructure settings.

### Get Retention Settings

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  system retention get
```

### Set Retention Field

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  system retention set --field logs_days --value 7
```

---

## Workflow: Plan Defaults

**Pattern**: Read-Process-Write

Manage default values for new plans.

### List Plan Defaults

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  plan defaults list
```

### Get Specific Default

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  plan defaults get --field commit_strategy
```

### Set Default Value

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  plan defaults set --field create_pr --value true
```

---

## API Reference

### Noun: skill-domains

| Verb | Parameters | Purpose |
|------|------------|---------|
| `list` | (none) | List all domains |
| `get` | `--domain` | Get full domain config (returns nested structure for technical domains) |
| `get-defaults` | `--domain` | Get default skills (returns `core.defaults` for nested domains) |
| `get-optionals` | `--domain` | Get optional skills (returns `core.optionals` for nested domains) |
| `set` | `--domain [--profile] [--defaults] [--optionals]` | Set domain config (use `--profile` for nested domains) |
| `add` | `--domain --defaults [--optionals]` | Add new domain |
| `validate` | `--domain --skill` | Check if skill valid (searches all profiles for nested domains) |
| `detect` | (none) | Auto-detect domains from project files |
| `get-extensions` | `--domain` | Get workflow skill extensions for domain |
| `set-extensions` | `--domain --type --skill` | Set workflow skill extension (types: outline, triage) |
| `get-available` | (none) | Get available domains based on detected build systems |
| `configure` | `--domains` | Configure selected domains with templates |

### resolve-domain-skills

| Parameters | Purpose |
|------------|---------|
| `--domain --profile` | Resolve skills for domain and profile (aggregates `{domain}.core` + `{domain}.{profile}`) |

Standard profiles: `implementation`, `testing`, `quality`.

### resolve-workflow-skill

| Parameters | Purpose |
|------------|---------|
| `--phase` | Resolve system workflow skill for phase (init, outline, plan, execute, finalize) |

Always returns from the `system` domain's `workflow_skills`.

### resolve-workflow-skill-extension

| Parameters | Purpose |
|------------|---------|
| `--domain --type` | Resolve domain-specific workflow extension (types: outline, triage) |

Returns null (not error) if extension doesn't exist for the domain.

### get-workflow-skills

| Parameters | Purpose |
|------------|---------|
| (none) | Get all workflow skills from system domain (5-phase model: init, outline, plan, execute, finalize) |

### Noun: modules

| Verb | Parameters | Purpose |
|------|------------|---------|
| `list` | (none) | List all modules with domains |
| `get` | `--module` | Get full module config |
| `get-domains` | `--module` | Get skill domains for module |
| `get-build-systems` | `--module` | Get available build systems for module |
| `get-command` | `--module --label` | Get command (static routing with default fallback) |
| `set-command` | `--module --label --command` | Set full command string for module |
| `add` | `--module --path --domains --build-systems` | Add new module |
| `set` | `--module [--domains] [--build-systems]` | Update module config |
| `remove` | `--module` | Remove module |
| `detect` | (none) | Auto-detect modules from pom.xml/build.gradle/package.json |

### Noun: build-systems

| Verb | Parameters | Purpose |
|------|------------|---------|
| `list` | (none) | List configured systems (detection reference only) |
| `get` | `--system` | Get specific build system config |
| `add` | `--system` | Add build system |
| `remove` | `--system` | Remove build system |
| `detect` | (none) | Auto-detect from project |

**Note**: `build_systems` section is for detection reference only. Commands are stored in `modules.{name}.commands` using static routing.

### Noun: system

| Verb | Parameters | Purpose |
|------|------------|---------|
| `retention get` | (none) | Get all retention settings |
| `retention set` | `--field --value` | Set retention field |

### Noun: plan

| Verb | Parameters | Purpose |
|------|------------|---------|
| `defaults list` | (none) | List all plan defaults |
| `defaults get` | `--field` | Get default value |
| `defaults set` | `--field --value` | Set default value |

### Noun: ci

| Verb | Parameters | Purpose |
|------|------------|---------|
| `get` | (none) | Get full CI config |
| `get-provider` | (none) | Get CI provider and repo URL |
| `get-tools` | (none) | Get authenticated tools list |
| `set-provider` | `--provider --repo-url` | Set CI provider |
| `set-tools` | `--tools` | Set authenticated tools (comma-separated) |

### init

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  init [--force]
```

---

## Data Model

### marshal.json Location

`.plan/marshal.json`

### Structure

The defaults template contains only `system` domain. Technical domains (java, javascript, etc.) are added during project initialization based on detection or manual configuration.

**Example** (Java project after init):

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
    }
  },
  "module_config": {
    "default": {
      "path": ".",
      "domains": ["java"],
      "build_systems": ["maven"],
      "type": "jar",
      "commands": {
        "module-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --goals \"clean test\"",
        "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --goals \"clean verify\"",
        "install": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --goals \"clean install\"",
        "quality-gate": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --goals \"clean install\" --profile pre-commit"
      }
    },
    "my-module": {
      "path": "my-module",
      "domains": ["java"],
      "build_systems": ["maven"],
      "type": "jar",
      "commands": {
        "module-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --goals \"clean test\" --module my-module",
        "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --goals \"clean verify\" --module my-module"
      }
    }
  },
  "build_systems": [
    {
      "system": "maven",
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
    }
  }
}
```

---

## Standard Domains

### System Domain

The `system` domain contains workflow skills (5-phase model) and base skills applied to all tasks.

| Field | Purpose |
|-------|---------|
| `defaults` | Base skills loaded for all tasks (`plan-marshall:general-development-rules`) |
| `optionals` | Optional base skills available for selection |
| `workflow_skills` | Maps 5 phases to workflow skill references |

**Workflow Phases**: `init`, `outline`, `plan`, `execute`, `finalize`

### Technical Domains (Profile Structure)

Technical domains use nested structure with `workflow_skill_extensions` and profiles.

| Profile | Phase | Purpose |
|---------|-------|---------|
| `core` | all | Skills loaded for all profiles |
| `implementation` | execute | Production code tasks |
| `testing` | execute | Test code tasks |
| `quality` | finalize | Documentation, verification |

**Available Domains**:

| Domain | Core Defaults | Extensions |
|--------|---------------|------------|
| `java` | `pm-dev-java:java-core` | outline, triage |
| `javascript` | `pm-dev-frontend:cui-javascript` | outline, triage |
| `plan-marshall-plugin-dev` | `pm-plugin-development:plugin-architecture` | triage |

Use `resolve-domain-skills --domain {domain} --profile {profile}` to get aggregated skills.

---

## Standard Command Labels

| Label | Purpose | Maven | Gradle | npm |
|-------|---------|-------|--------|-----|
| `compile` | Compile source | `compile` | `compileJava` | `run build` |
| `test` | Run unit tests | `clean test` | `clean test` | `run test` |
| `verify` | Full verification | `clean verify` | `clean check` | `run test && run lint` |
| `install` | Install artifacts | `clean install` | `publishToMavenLocal` | - |
| `pre-commit` | Pre-commit checks | `-Ppre-commit clean install` | `preCommit` | - |
| `coverage` | Coverage analysis | `-Pcoverage clean verify` | `jacocoTestReport` | `run test:coverage` |

---

## Scripts

| Script | Notation |
|--------|----------|
| plan-marshall-config | `plan-marshall:plan-marshall-config` |

Script characteristics:
- Uses Python stdlib only (json, argparse, pathlib, xml.etree)
- Outputs TOON to stdout
- Exit code 0 for success, 1 for errors
- Supports `--help` flag

---

## Integration Points

### With plan-marshall Skill
- Called during wizard initialization
- Called from configuration menus

### With Implementation Agents
- `skill-domains get-defaults` provides skills to load
- `skill-domains get-optionals` provides available optionals

### With Build Commands
- `modules get-command` resolves build commands using static routing
- `modules set-command` allows custom command configuration
- Commands are generated by `plan-marshall:extension-api:build_env persist`

### With Cleanup
- `system retention get` provides retention settings

---

## Error Handling

All operations validate prerequisites before proceeding:

```toon
status: error
error: marshal.json not found. Run command /marshall-steward first
```

Standard error conditions:
- `marshal.json not found` - Run `/marshall-steward` first
- `skill_domains not configured` - Run `/marshall-steward` first
- `Unknown domain: {name}` - Domain doesn't exist
- `Unknown module: {name}` - Module doesn't exist
- `Build system not found: {name}` - Build system not configured
