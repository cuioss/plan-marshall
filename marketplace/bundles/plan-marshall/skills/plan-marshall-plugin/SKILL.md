---
name: plan-marshall-plugin
description: Build system module discovery consolidating Maven, Gradle, npm, and Python detection
user-invocable: false
---

# Plan Marshall Plugin - Build Discovery

Consolidates module discovery for all build systems (Maven, Gradle, npm, Python) into a single extension point. Build execution scripts live in sibling skill directories (`build-maven`, `build-gradle`, `build-npm`, `build-python`).

## Extension API

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Returns domain key `build` with empty profiles |
| `discover_modules(project_root)` | Discover modules across Maven, Gradle, npm, and Python |

## Discovery Delegation

- Maven: `build-maven/scripts/_maven_cmd_discover.py`
- Gradle: `build-gradle/scripts/_gradle_cmd_discover.py`
- npm: Uses `extension_base.discover_descriptors()` + npm commands via `build-npm/scripts/npm.py`
- Python: Parses `pyproject.toml` for pyprojectx aliases

## Integration

This extension is discovered by:
- `extension-api` - Build system detection and command generation
- `marshall-steward` - Project setup wizard
