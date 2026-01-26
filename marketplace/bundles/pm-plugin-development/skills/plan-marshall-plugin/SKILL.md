---
name: plan-marshall-plugin
description: Plugin development domain manifest with module discovery for plan-marshall workflow integration
user-invocable: false
allowed-tools: Read
---

# Plan Marshall Plugin - Plugin Development Domain

Domain manifest skill providing plugin development capabilities and module discovery for plan-marshall workflows.

## Purpose

Provides two key capabilities:

1. **Domain Configuration** - Declares the plan-marshall-plugin-dev domain with profile-based skill organization
2. **Module Discovery** - Discovers marketplace bundles for `.plan/project-architecture/derived-data.json` generation

## Mutual Exclusivity

This extension is **mutually exclusive** with `pm-dev-python:plan-marshall-plugin` for module discovery:

| Project Type | Handled By |
|-------------|------------|
| plan-marshall marketplace | This extension (`pm-plugin-development`) |
| Other Python projects | `pm-dev-python` |

Detection uses `marketplace/.claude-plugin/marketplace.json`:
- If `name` field equals `"plan-marshall"` → this extension provides module discovery
- Otherwise → skip (pm-dev-python handles it)

This avoids duplicate modules when both extensions are active.

---

## Module Discovery

Discovers Claude Code marketplace bundles as modules. Each bundle in `marketplace/bundles/` becomes a module with:

| Aspect | Value |
|--------|-------|
| Build system | `marshall-plugin` |
| Descriptor | `.claude-plugin/plugin.json` |
| Packages | Skills, agents, commands (type-prefixed) |

### Canonical Commands

Each bundle module gets the full set of canonical Python build commands via `pm-dev-python:plan-marshall-plugin:python_build`:

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

## Configuration

All configuration is in `extension.py` which implements the Extension API:

| Method | Purpose |
|--------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `discover_modules()` | Module discovery for derived-data.json |
| `provides_triage()` | Triage skill reference |
| `provides_outline()` | Outline skill reference |

### Capabilities

Domain capabilities for `${domain}` placeholder resolution:

```json
"capabilities": {
  "triage": "pm-plugin-development:ext-triage-plugin"
}
```

Only triage capability is provided. Verification steps requiring `quality-gate` or `build-verify` are skipped for this domain.

## Dependencies

This skill depends on:
- `pm-dev-python:plan-marshall-plugin` - Python build execution via python_build.py

## Integration

This extension is discovered by:
- `plan-marshall:extension-api` - Module discovery aggregation
- `plan-marshall:analyze-project-architecture` - Architecture analysis
- `marshall-steward` wizard - Domain selection during project setup
