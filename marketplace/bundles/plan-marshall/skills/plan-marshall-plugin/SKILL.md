---
name: plan-marshall-plugin
description: Build system module discovery consolidating Maven, Gradle, npm, and Python detection
implements: plan-marshall:extension-api/standards/ext-point-domain-bundle
user-invocable: false
mode: manifest
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
- `derive_edges()` must stay a pure function of its arguments — no filesystem access, no subprocess, and no language server booted inside it. The harvest is a discovery-time engine; this resolver is a pure join over its output

---

Consolidates module discovery for all build systems (Maven, Gradle, npm, Python) into a single extension point. Also provides the `general-dev` domain with cross-cutting development skills, the Axis-D path attribution for the `.plan` tree, and the Axis-C `lsp` derivation resolver. Build execution scripts live in sibling skill directories (`build-maven`, `build-gradle`, `build-npm`, `build-pyproject`).

See [extension-contract.md](../extension-api/standards/extension-contract.md) for the complete ExtensionBase contract.

## Extension API

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Returns the `general-dev` domain (cross-cutting dev skills) |
| `discover_modules(project_root)` | Discover modules across Maven, Gradle, npm, and Python |
| `provides_recipes()` | Returns the `code-review`, `refactor-to-profile-standards`, `security-audit`, `agentfile-hygiene`, and `surgical-fix` recipes |
| `applies_to_module(module_data)` | Applies general-dev skills to modules with code build systems |
| `path_attributor_id()` | Returns the Axis-D provenance id `plan-marshall`, stamped onto every path this attributor claims |
| `claim_paths()` | Declares the repo-relative trees the `plan-marshall` module owns — the bare `.plan` root segment |
| `derivation_resolver_id()` | Returns the Axis-C provenance id `lsp`, stamped onto every edge this resolver produces |
| `derivation_file_patterns()` | Declares the file patterns the harvest reads (`['**/*.py']`). Descriptive metadata for the resolver-configuration menu, never a filter |
| `derive_edges()` | Pure join over the `component_refs` field discovery materializes, selecting only `lsp` entries. Reads the `lsp_harvest` status record and reports it, so a harvest that did not run is stated rather than collapsing into a zero-edge success. Unresolved targets, unknown endpoints, and self-edges are suppressed and reported as aggregated `notes[]` entries |

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
- Python: `build-pyproject/scripts/_pyproject_cmd_discover.py`
