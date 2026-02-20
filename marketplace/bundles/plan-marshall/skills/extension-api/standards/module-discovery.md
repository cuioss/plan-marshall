# Module Discovery Contract

Primary API for module discovery — returns comprehensive module information for project analysis and build command resolution.

## Purpose

Provides the extension hook for discovering project modules with complete metadata. This is the primary API for project analysis, enabling:

- Module discovery with paths, metadata, packages, dependencies, and stats
- Build command resolution via canonical commands
- Multi-technology support through extension-based discovery
- Virtual module splitting for directories with multiple build systems

---

## Lifecycle Position

The method is invoked during project analysis:

```
1. Extension discovery and loading
2. discover_project_modules() aggregates across all extensions
3. ➤ discover_modules(project_root) → modules per extension
4. Results persisted to .plan/project-structure.json
5. Consumed by phase-4-plan for task creation
6. Consumed by build commands for execution
```

**Timing**: Called by `discover_project_modules()` in `extension_discovery.py` during project analysis (typically via `/marshall-steward` or `analyze-project-architecture`). Results are persisted and consumed throughout the planning lifecycle.

---

## Method Signature

```python
def discover_modules(self, project_root: str) -> list:
    """Discover all modules with complete metadata.

    This is the primary API for module discovery. Returns comprehensive
    module information including metadata, dependencies, packages, and stats.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts. See build-project-structure.md for complete
        output structure including paths, metadata, packages, dependencies,
        stats, and commands fields.

    Default: []
    """
    return []
```

---

## Output Summary

Each module dict contains:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Module name (includes technology suffix for virtual modules) |
| `build_systems` | list[str] | Single build system (e.g., `["maven"]`) |
| `paths` | dict | Module paths (`module`, `descriptor`, `sources`, `tests`, `readme`) |
| `metadata` | dict | Build-system-specific metadata (snake_case fields) |
| `packages` | dict | Package name → path mapping |
| `dependencies` | list[str] | Technology-native format |
| `stats` | dict | `{source_files, test_files}` |
| `commands` | dict | Canonical command name → resolved command string |

See [build-project-structure.md](build-project-structure.md) for the complete output specification including field types, virtual module structure, profile structure, and compliance checklist.

---

## Implementation Pattern

Use `discover_descriptors()` and `build_module_base()` from `build_discover.py` for common discovery logic, then enrich with domain-specific metadata:

```python
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Domain extension with module discovery."""

    def discover_modules(self, project_root: str) -> list:
        """Discover modules in the project."""
        from build_discover import discover_descriptors, build_module_base
        descriptors = discover_descriptors(project_root, "pom.xml")

        modules = []
        for desc_path in descriptors:
            base = build_module_base(project_root, desc_path)
            modules.append({
                "name": base.name,
                "build_systems": ["maven"],
                "paths": base.paths.to_dict(),
                "metadata": {},       # Domain-specific enrichment
                "packages": {},       # Package discovery
                "dependencies": [],   # Dependency extraction
                "stats": {"source_files": 0, "test_files": 0},
                "commands": self._resolve_commands(base)
            })
        return modules
```

### Canonical Commands

Each module must include a `commands` dict mapping canonical command names to executable strings. See [canonical-commands.md](canonical-commands.md) for the command vocabulary, resolution logic, and requirements.

---

## Existing Implementations

| Bundle | Domain | Build System | Discovery Method |
|--------|--------|-------------|-----------------|
| pm-dev-java | java | Maven, Gradle | `maven_cmd_discover.py`, `gradle_cmd_discover.py` |
| pm-dev-frontend | javascript | npm | Inline in `extension.py` |
| pm-documents | documentation | — | Directory-based (doc dirs) |
| pm-plugin-development | plan-marshall-plugin-dev | — | Bundle-based (marketplace bundles) |
| pm-requirements | requirements | — | Spec file discovery |

Bundles returning `[]`: pm-dev-java-cui (additive, no own modules).

---

## Design Rationale

### Why Extension-Based?

Module discovery is handled by extensions rather than a central scanner because:

1. **Multi-technology** — each domain knows its own descriptor files and metadata format
2. **Domain enrichment** — extensions add domain-specific metadata, packages, and dependencies
3. **Command resolution** — extensions know how to map canonical commands to build-system-specific invocations

### Why Virtual Module Splitting?

Directories with multiple build systems (e.g., `pom.xml` + `package.json`) are split into virtual modules because:

1. **Single build system per module** — no ambiguity in command resolution
2. **Technology-specific skills** — each virtual module gets its own skill profile
3. **Independent task assignment** — tasks target a single technology

---

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract
- [build-project-structure.md](build-project-structure.md) — Complete output specification
- [canonical-commands.md](canonical-commands.md) — Command vocabulary and resolution
- [build-base-libs.md](build-base-libs.md) — Base library API (`discover_descriptors`, `build_module_base`)
- [orchestrator-integration.md](../../analyze-project-architecture/standards/orchestrator-integration.md) — Orchestrator flow and hybrid merging
