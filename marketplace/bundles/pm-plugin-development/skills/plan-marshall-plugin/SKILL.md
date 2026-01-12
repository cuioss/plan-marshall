---
name: plan-marshall-plugin
description: Plugin development domain manifest with module discovery for plan-marshall workflow integration
allowed-tools: Read
---

# Plan Marshall Plugin - Plugin Development Domain

Domain manifest skill providing plugin development capabilities and module discovery for plan-marshall workflows.

## Purpose

Provides two key capabilities:

1. **Domain Configuration** - Declares the plan-marshall-plugin-dev domain with profile-based skill organization
2. **Module Discovery** - Discovers marketplace bundles for `.plan/project-architecture/derived-data.json` generation

## Module Discovery

Discovers Claude Code marketplace bundles as modules. Each bundle in `marketplace/bundles/` becomes a module with:

| Aspect | Value |
|--------|-------|
| Build system | `marshall-plugin` |
| Descriptor | `.claude-plugin/plugin.json` |
| Packages | Skills, agents, commands (type-prefixed) |
| Tests | `python3 test/run-tests.py test/{bundle}` |
| Quality gate | `/plugin-doctor --bundle {name}` |

### Package Types

Components are mapped to packages with type prefixes:

- `skill:{name}` - Skill directories (description from SKILL.md)
- `agent:{name}` - Agent .md files (description from frontmatter)
- `command:{name}` - Command .md files (description from frontmatter)

### Root Module

A "default" root module is included with:
- `module-tests`: `python3 test/run-tests.py` (all tests)
- `quality-gate`: `/plugin-doctor marketplace`

## Configuration

All configuration is in `extension.py` which implements the Extension API:

| Method | Purpose |
|--------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `discover_modules()` | Module discovery for derived-data.json |
| `provides_triage()` | Triage skill reference |
| `provides_outline()` | Outline skill reference |

## Integration

This extension is discovered by:
- `plan-marshall:extension-api` - Module discovery aggregation
- `plan-marshall:analyze-project-architecture` - Architecture analysis
- `marshall-steward` wizard - Domain selection during project setup
