---
name: plan-marshall-plugin
description: Plugin development domain manifest with module discovery for plan-marshall workflow integration
user-invocable: false
---

# Plan Marshall Plugin - Plugin Development Domain

Domain extension providing plugin development skill registration and module discovery to plan-marshall workflows.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Domain identity must match the bundle name convention (plan-marshall-plugin-dev)
- Profile-based skill organization must align with plugin.json registration
- Module discovery must detect marketplace.json to avoid conflicts with pm-dev-python

## Purpose

- Domain identity and workflow extensions (triage, outline)
- Profile-based skill organization for plugin development projects
- Module discovery for marketplace bundles
- Mutual exclusivity with `pm-dev-python:plan-marshall-plugin` via marketplace.json detection

## Module Discovery

Discovers marketplace bundles as modules for the per-module architecture
layout under `.plan/project-architecture/`. `manage-architecture` writes a
top-level `_project.json` whose `modules` index is the source of truth for
which modules exist, plus one `{module}/derived.json` per indexed module
holding this extension's discovery output. Per-module subdirectories present
on disk but absent from `_project.json["modules"]` are ignored — the index is
authoritative, not the filesystem.

Each bundle in `marketplace/bundles/` becomes one such module with:

| Aspect | Value |
|--------|-------|
| Build system | `marshall-plugin` |
| Descriptor | `.claude-plugin/plugin.json` |
| Packages | Skills, agents, commands (type-prefixed) |

### Canonical Commands

Each bundle module gets the full set of canonical Python build commands via `plan-marshall:build-python:python_build`:

| Command | Execution |
|---------|-----------|
| `compile` | mypy on bundle sources |
| `test-compile` | mypy on bundle tests |
| `module-tests` | pytest on bundle tests |
| `quality-gate` | ruff check on bundle |
| `verify` | Full verification (compile + quality-gate + module-tests) |
| `coverage` | pytest with coverage |
| `clean` | Remove build artifacts |

### Package Types

Components are mapped to packages with type prefixes:

- `skill:{name}` - Skill directories (description from SKILL.md)
- `agent:{name}` - Agent .md files (description from frontmatter)
- `command:{name}` - Command .md files (description from frontmatter)

### Root Module

A "default" root module provides project-wide commands (no bundle filter):
- All canonical commands without bundle argument run against entire project

## Extension API

Configuration in `extension.py` implements the Extension API contract:

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `discover_modules()` | Module discovery whose results feed each bundle's per-module `derived.json` under `.plan/project-architecture/{module}/` |
| `provides_triage()` | Returns `pm-plugin-development:ext-triage-plugin` |
| `provides_outline_skill()` | Returns `pm-plugin-development:ext-outline-workflow` |

## Integration

This extension is discovered by:
- `extension-api` - Domain registration and module discovery
- `manage-architecture` - Architecture analysis
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `pm-dev-python:plan-marshall-plugin` - Python build execution via python_build.py
- `pm-plugin-development:ext-triage-plugin` - Plugin triage extension
- `pm-plugin-development:ext-outline-workflow` - Plugin outline workflow
