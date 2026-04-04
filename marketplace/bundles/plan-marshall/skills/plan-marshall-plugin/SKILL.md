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

Consolidates module discovery for all build systems (Maven, Gradle, npm, Python) into a single extension point. Also provides the `general-dev` domain with cross-cutting development skills. Build execution scripts live in sibling skill directories (`build-maven`, `build-gradle`, `build-npm`, `build-python`).

See [extension-contract.md](../extension-api/standards/extension-contract.md) for the complete ExtensionBase contract.

## Extension API

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Returns `build` domain (empty profiles) + `general-dev` domain (cross-cutting dev skills) |
| `discover_modules(project_root)` | Discover modules across Maven, Gradle, npm, and Python |
| `provides_recipes()` | Returns `refactor-to-profile-standards` recipe |
| `applies_to_module(module_data)` | Applies general-dev skills to modules with code build systems |

## Discovery Flow

The extension scans the project root for build system markers:

| Marker File | Build System |
|-------------|-------------|
| `pom.xml` | Maven |
| `build.gradle` / `build.gradle.kts` | Gradle |
| `package.json` | npm |
| `pyproject.toml` | Python (pyprojectx) |

Each detected build system delegates to its corresponding discovery script. Results from all build systems are collected and, when multiple build systems coexist at the same path, split into separate virtual modules with technology suffixes (e.g., `my-module-maven`, `my-module-npm`).

## Discovery Delegation

- Maven: `build-maven/scripts/_maven_cmd_discover.py`
- Gradle: `build-gradle/scripts/_gradle_cmd_discover.py`
- npm: `build-npm/scripts/_npm_cmd_discover.py`
- Python: `build-python/scripts/_python_cmd_discover.py`
