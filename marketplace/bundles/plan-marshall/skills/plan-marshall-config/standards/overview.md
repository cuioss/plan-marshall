# Plan-Marshall Config Overview

Project-level infrastructure configuration for Claude Code marketplace projects.

## Purpose

The `plan-marshall-config` skill manages `.plan/marshal.json`, providing a centralized configuration for:

- **Skill Domains**: Which implementation skills to load per development domain
- **System Settings**: Retention and cleanup configuration
- **Plan Defaults**: Default values applied to new plans
- **CI Configuration**: Provider settings and authenticated tools

## Design Principles

### 1. Skills Define Their Own Behavior

Domain routing and workflow skills are configured in marshal.json's `skill_domains` section. This skill manages project-specific infrastructure.

### 2. Noun-Verb API Pattern

All operations follow the `{noun} {verb}` pattern:

```bash
plan-marshall-config skill-domains list
plan-marshall-config system retention get
plan-marshall-config ci get-provider
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
| `system` | Retention settings for cleanup |
| `plan` | Default values for new plans |
| `ci` | CI provider configuration |

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
- Detect and configure skill domains
- Configure retention settings

### With Implementation Agents

Agents query skill domains to load appropriate skills:

```bash
# Get skills to load for Java core domain
plan-marshall-config skill-domains get-defaults --domain java-core
```

### With Cleanup Scripts

Cleanup uses retention settings:

```bash
plan-marshall-config system retention get
```

## Related Documentation

- [data-model.md](data-model.md) - JSON structure and field definitions
- [api-reference.md](api-reference.md) - Complete API with examples
- [skill-domains.md](skill-domains.md) - Skill domain management
