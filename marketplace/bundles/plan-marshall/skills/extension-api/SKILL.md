---
name: extension-api
description: Extension API for domain bundle discovery, module detection, and canonical command generation
user-invocable: false
---

# Extension API Skill

## Enforcement

- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery ...`
- Never import extension modules directly outside of build scripts
- All CLI output follows TOON format contract

---

Unified API for domain bundle extensions providing module discovery, build system detection, and command generation. Provides the `ExtensionBase` abstract base class that all domain extensions must inherit from.

## Purpose

- **ExtensionBase ABC** - Abstract base class with required/optional methods
- **Canonical constants** - `CMD_*` constants for command names
- **Profile patterns** - `PROFILE_PATTERNS` vocabulary for classification
- **Discovery utilities** - Loading and discovering extensions
- **Build utilities** - Module discovery, log file management, issue parsing

## When to Reference This Skill

Reference when:
- Creating a new `extension.py` for a domain bundle
- Implementing `discover_modules()` for a build system
- Understanding canonical command names and resolution
- Parsing build output and handling issues

## Skill Structure

```
extension-api/
├── SKILL.md                        # This file
├── scripts/
│   ├── extension_base.py           # ExtensionBase ABC, canonical commands
│   ├── extension_discovery.py      # Extension discovery, loading, aggregation
│   ├── _build_discover.py          # Module discovery, path building
│   ├── _build_result.py            # Log file creation, result construction (co-located build utility)
│   ├── _build_parse.py             # Issue structures, warning filtering (co-located build utility)
│   ├── _build_format.py            # TOON and JSON output formatting (co-located build utility)
│   ├── _build_wrapper.py           # Build tool wrapper detection (co-located build utility)
│   └── _module_aggregation.py      # Virtual module splitting
└── standards/
    ├── extension-contract.md       # Extension API contract (all methods, hooks, validation)
    ├── module-discovery.md         # Module discovery contract + output specification
    ├── canonical-commands.md       # Command vocabulary and resolution
    ├── build-execution.md          # Build execution API + return structure
    ├── profiles.md                 # Profile override mechanism + profile contracts
    └── workflow-overview.md        # 6-phase workflow + user review gate
```

---

## Quick Reference

All extensions **must** inherit from `ExtensionBase` and implement required methods.

### Required Methods (Abstract)

| Method | Purpose |
|--------|---------|
| `get_skill_domains() -> list[dict]` | Return domain metadata with profiles |

### Primary Methods

| Method | Default | Purpose |
|--------|---------|---------|
| `discover_modules(project_root: str) -> list` | `[]` | Discover modules with paths, metadata, stats, commands |

### Optional Methods (With Defaults)

| Method | Default | Purpose |
|--------|---------|---------|
| `config_defaults(project_root: str) -> None` | no-op | Configure project defaults (called during init) |
| `provides_triage() -> str \| None` | `None` | Return triage skill reference |
| `provides_outline_skill() -> str \| None` | `None` | Return domain-specific outline skill reference |
| `provides_verify_steps() -> list[dict]` | `[]` | Return domain-specific verification steps |

---

## 4-Layer Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAYER 1: PHASE SKILLS (System only - NO domain override)       │
│  phase-1-init → phase-2-refine → phase-3-outline → phase-4-plan │
│    → phase-5-execute → phase-6-finalize                          │
│                            │                                     │
│                            │ delegates to                        │
│                            ▼                                     │
│  LAYER 2: PROFILE SKILLS (System default, domain CAN override)  │
│  task-implementation (profile=implementation)                    │
│  task-module-testing (profile=module_testing)                    │
│                            │                                     │
│                            │ loads                               │
│                            ▼                                     │
│  LAYER 3: EXTENSIONS (Domain provides, loaded BY system skills) │
│  outline-ext: Codebase analysis, deliverable patterns            │
│  triage-ext: Suppression syntax, severity guidelines             │
│                            │                                     │
│                            │ loads                               │
│                            ▼                                     │
│  LAYER 4: DOMAIN SKILLS (Loaded from task.skills at execution)  │
│  java-core, java-cdi, junit-core, javascript, etc.           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Extension Point | Override Model | Contract Location |
|-------|-----------------|----------------|-------------------|
| **Phase Skills** | None | System only, no override | Phase SKILL.md files |
| **Profile Skills** | workflow_skills in marshal.json | Domain can replace default | [profiles/](standards/) |
| **Extensions** | provides_*() in extension.py | Additive (domain provides) | [extensions](standards/) |
| **Domain Skills** | skills_by_profile in module analysis | Selected per deliverable | Domain bundle SKILL.md |

---

## Architecture (Optional)

For understanding the complete system architecture, reference these documents:

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [extension-contract.md](standards/extension-contract.md) | Complete extension API contract (all methods, hooks, validation) | Creating or modifying an extension |
| [module-discovery.md](standards/module-discovery.md) | Module discovery + output specification | Implementing `discover_modules()` |
| [canonical-commands.md](standards/canonical-commands.md) | Command vocabulary and resolution | Implementing `discover_modules()` commands |
| [build-execution.md](standards/build-execution.md) | Build execution API + return structure | Running build commands, formatting output |
| [profiles.md](standards/profiles.md) | Profile override mechanism + contracts | Understanding/overriding profile skills |
| [workflow-overview.md](standards/workflow-overview.md) | 6-phase workflow + user review gate | Understanding phase transitions and contracts |

**Note**: These documents define the target architecture. Implementation may be in progress.

---

## Scripts

### Extension Framework (Public API)

| Script | Type | Purpose |
|--------|------|---------|
| `extension_base.py` | Library | ExtensionBase ABC, canonical commands, profile patterns |
| `extension_discovery.py` | Library + CLI | Extension discovery, loading, aggregation, config defaults |
| `_build_discover.py` | Library | Module discovery, path building, README detection |
| `_module_aggregation.py` | Library | Virtual module splitting |

### Build Execution Utilities (Co-Located, Not Part of Extension API)

These are co-located here for PYTHONPATH convenience but are NOT part of the extension API. They are imported directly by build scripts (`build-maven`, `build-npm`, etc.), not through `extension_base`.

| Script | Type | Purpose |
|--------|------|---------|
| `_build_result.py` | Library | Log file creation, result dict construction |
| `_build_parse.py` | Library | Issue structures, warning filtering |
| `_build_format.py` | Library | TOON and JSON output formatting |
| `_build_wrapper.py` | Library | Build tool wrapper detection |

### CLI Commands

The `extension_discovery.py` script provides CLI commands for extension operations:

```bash
# Apply config_defaults() callback for all extensions
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery apply-config-defaults
```

**Output (TOON)**:
```toon
status	success
extensions_called	3
extensions_skipped	2
errors_count	0
```

### Python Import Usage

The executor sets PYTHONPATH to include `extension-api/scripts/`, so imports work directly:

```python
# Extension framework (public API via extension_base re-exports)
from extension_base import (
    ExtensionBase,
    discover_descriptors,    # Re-exported from _build_discover
    build_module_base,       # Re-exported from _build_discover
    find_readme,             # Re-exported from _build_discover
    CMD_VERIFY,
    CMD_MODULE_TESTS,
)

# Discovery functions
from extension_discovery import (
    discover_all_extensions,
    discover_project_modules,
    get_skill_domains_from_extensions,
    apply_config_defaults,
)

# Build utilities (co-located, not part of extension API)
from _build_result import (
    create_log_file,
    success_result,
    error_result,
)

from _build_parse import (
    Issue,
    filter_warnings,
    partition_issues,
)
```

---

## Canonical Command Constants

Import from `extension_base` for type-safe command references:

```python
from extension_base import (
    CMD_CLEAN,             # "clean"
    CMD_COMPILE,           # "compile"
    CMD_TEST_COMPILE,      # "test-compile"
    CMD_MODULE_TESTS,      # "module-tests"
    CMD_INTEGRATION_TESTS, # "integration-tests"
    CMD_COVERAGE,          # "coverage"
    CMD_BENCHMARK,         # "benchmark"
    CMD_QUALITY_GATE,      # "quality-gate"
    CMD_VERIFY,            # "verify"
    CMD_INSTALL,           # "install"
    CMD_CLEAN_INSTALL,     # "clean-install"
    CMD_PACKAGE,           # "package"
    ALL_CANONICAL_COMMANDS,
    PROFILE_PATTERNS,      # Profile ID to canonical mapping (for internal use)
)
```

| Constant | Value | Required | Description |
|----------|-------|----------|-------------|
| `CMD_CLEAN` | `clean` | No | Remove build artifacts |
| `CMD_QUALITY_GATE` | `quality-gate` | Yes | Static analysis, linting |
| `CMD_VERIFY` | `verify` | Yes* | Full verification (*non-pom modules) |
| `CMD_MODULE_TESTS` | `module-tests` | Conditional | Unit tests (if tests exist) |
| `CMD_COMPILE` | `compile` | No | Compile production sources |
| `CMD_TEST_COMPILE` | `test-compile` | No | Compile test sources |
| `CMD_INTEGRATION_TESTS` | `integration-tests` | No | Integration tests |
| `CMD_COVERAGE` | `coverage` | No | Coverage measurement |
| `CMD_BENCHMARK` | `benchmark` | No | Benchmark/performance tests |
| `CMD_INSTALL` | `install` | No | Install to local repository |
| `CMD_CLEAN_INSTALL` | `clean-install` | No | Clean and install combined |
| `CMD_PACKAGE` | `package` | No | Create deployable artifact |

**Note**: `clean` is a separate command. Other commands do NOT include clean goal.

See [canonical-commands.md](standards/canonical-commands.md) for command resolution logic.

---

## Minimal Extension Template

```python
#!/usr/bin/env python3
"""Extension API for {bundle-name} bundle."""

from pathlib import Path
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Extension for {bundle-name} bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [{
            "domain": {
                "key": "domain-key",
                "name": "Domain Name",
                "description": "Domain description"
            },
            "profiles": {
                "core": {"defaults": [], "optionals": []},
                "implementation": {"defaults": [], "optionals": []},
                "module_testing": {"defaults": [], "optionals": []},
                "quality": {"defaults": [], "optionals": []}
            }
        }]

    def discover_modules(self, project_root: str) -> list:
        """Discover modules in the project.

        Returns list of module dicts with:
        - name, build_systems, paths, metadata, packages, dependencies, stats, commands
        """
        # Find descriptors
        from build_discover import discover_descriptors, build_module_base
        descriptors = discover_descriptors(project_root, "descriptor-file")

        modules = []
        for desc_path in descriptors:
            base = build_module_base(project_root, desc_path)
            # Enrich with extension-specific metadata, stats, commands
            modules.append({
                "name": base.name,
                "build_systems": ["my-build-system"],
                "paths": base.paths.to_dict(),
                "metadata": {},
                "packages": {},
                "dependencies": [],
                "stats": {"source_files": 0, "test_files": 0},
                "commands": self._resolve_commands(base)
            })
        return modules
```

---

## Integration Points

- **manage-architecture** - Orchestrates extensions, owns `.plan/project-architecture/*.json` files
- **manage-config** - Uses `discover_all_extensions()` for domain configuration
- **Domain bundles** - Implement `extension.py` inheriting from `ExtensionBase`

