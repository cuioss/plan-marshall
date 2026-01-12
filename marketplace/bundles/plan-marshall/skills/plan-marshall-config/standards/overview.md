# Plan-Marshall Config Overview

Project-level infrastructure configuration for Claude Code marketplace projects.

## Purpose

The `plan-marshall-config` skill manages `.plan/marshal.json`, providing a centralized configuration for:

- **Skill Domains**: Which implementation skills to load per development domain
- **Modules**: Project module structure with domain and build system mappings
- **Build Systems**: Available build systems with command configurations
- **System Settings**: Retention and cleanup configuration
- **Plan Defaults**: Default values applied to new plans

## Design Principles

### 1. Skills Define Their Own Behavior

Domain routing and workflow skills are configured in marshal.json's `skill_domains` section. This skill manages project-specific infrastructure.

### 2. Noun-Verb API Pattern

All operations follow the `{noun} {verb}` pattern:

```bash
plan-marshall-config skill-domains list
plan-marshall-config modules get --module my-core
plan-marshall-config build-systems detect
```

### 3. TOON Output Format

All commands output TOON (Token-Oriented Object Notation) for token efficiency:

```toon
status: success
domain: java-core
defaults[1]:
- pm-dev-java:java-core
```

### 4. Fail Early, Fail Loud

Operations validate prerequisites before proceeding. Missing marshal.json produces a clear error directing users to run `/marshall-steward`.

## marshal.json Scope

The configuration file contains **only project-specific infrastructure**:

| Section | Purpose |
|---------|---------|
| `skill_domains` | Implementation skill defaults/optionals per domain |
| `modules` | Project modules with domain/build-system mappings |
| `build_systems` | Build system commands and skills |
| `system` | Retention settings for cleanup |
| `plan` | Default values for new plans |

## What Does NOT Belong in marshal.json

These configurations do not belong in marshal.json:

- File pattern routing (deprecated)
- Keyword detection (deprecated)

## File Location

```
.plan/marshal.json
```

Created by `/marshall-steward` wizard or `plan-marshall-config init`.

## Integration Points

### With /marshall-steward Command

The wizard uses this skill to:
- Initialize marshal.json
- Detect build systems
- Configure retention settings

### With Implementation Agents

Agents query skill domains to load appropriate skills:

```bash
# Get skills to load for Java core domain
plan-marshall-config skill-domains get-defaults --domain java-core
```

### With Build Commands

Build commands resolve module-specific commands:

```bash
# Get verify command for a module (with override resolution)
plan-marshall-config modules get-command --module my-ui --system npm --label verify
```

### With Cleanup Scripts

Cleanup uses retention settings:

```bash
plan-marshall-config system retention get
```

## Related Documentation

- [data-model.md](data-model.md) - JSON structure and field definitions
- [api-reference.md](api-reference.md) - Complete API with examples
- [modules.md](modules.md) - Module configuration details
- [skill-domains.md](skill-domains.md) - Skill domain management
- [build-systems.md](build-systems.md) - Build system configuration
