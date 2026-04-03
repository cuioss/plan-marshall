---
name: plan-marshall-plugin
description: Build system module discovery consolidating Maven, Gradle, npm, and Python detection
user-invocable: false
---

# Plan Marshall Plugin - Build Discovery

## Enforcement

**Execution mode**: Reference module — loaded by extension-api for build system discovery.

**Prohibited actions:**
- Do not call discovery scripts directly; use extension-api commands instead
- Do not modify discovery delegation order
- Do not alter build system marker detection logic without updating all delegated scripts

**Constraints:**
- Module discovery is read-only — no file system mutations
- Results are consumed by manage-architecture and marshall-steward
- All discovery invocations flow through the extension-api entry point

---

Consolidates module discovery for all build systems (Maven, Gradle, npm, Python) into a single extension point. Build execution scripts live in sibling skill directories (`build-maven`, `build-gradle`, `build-npm`, `build-python`).

## Extension API

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Returns domain key `build` with empty profiles |
| `discover_modules(project_root)` | Discover modules across Maven, Gradle, npm, and Python |

## Discovery Flow

The extension scans the project root for build system markers to determine which build systems are present:

| Marker File | Build System |
|-------------|-------------|
| `pom.xml` | Maven |
| `build.gradle` / `build.gradle.kts` | Gradle |
| `package.json` | npm |
| `pyproject.toml` | Python (pyprojectx) |

Each detected build system delegates to its corresponding discovery script, which parses the build descriptor to extract module names and paths. Results from all build systems are collected and, when multiple build systems coexist at the same path, split into separate virtual modules with technology suffixes (e.g., `my-module-maven`, `my-module-npm`).

When multiple build systems coexist in the same project (e.g., Maven for backend and npm for frontend), the extension merges all discovered modules into a single flat list.

## Discovery Delegation

- Maven: `build-maven/scripts/_maven_cmd_discover.py`
- Gradle: `build-gradle/scripts/_gradle_cmd_discover.py`
- npm: Uses `extension_base.discover_descriptors()` + npm commands via `build-npm/scripts/npm.py`
- Python: Parses `pyproject.toml` for pyprojectx aliases

## TOON Output Example

```toon
status	success
build_systems	maven,npm
total_modules	5

modules[5]{name,build_system,path}:
core,maven,modules/core
api,maven,modules/api
web,npm,packages/web
shared,npm,packages/shared
tools,npm,packages/tools
```

## Related Skills

- `extension-api` — Loads this extension for build detection
- `build-maven`, `build-gradle`, `build-npm`, `build-python` — Delegated discovery scripts
- `manage-architecture` — Consumes discovery results for project analysis
- `marshall-steward` — Uses discovery for project setup

## Integration

This extension is discovered by:
- `extension-api` - Build system detection and command generation
- `marshall-steward` - Project setup wizard
