---
name: extension-api
description: Extension API for domain bundle discovery, module detection, and canonical command generation
user-invocable: false
---

# Extension API Skill

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
│   ├── _build_discover.py           # Module discovery, path building
│   ├── _build_result.py            # Log file creation, result construction
│   ├── _build_parse.py             # Issue structures, warning filtering
│   ├── _build_format.py            # TOON and JSON output formatting
│   ├── _build_wrapper.py           # Build tool wrapper detection
│   └── _module_aggregation.py      # Virtual module splitting
└── standards/
    ├── extension-contract.md       # Extension API contract
    ├── skill-domains.md            # Skill domains contract (required method)
    ├── module-discovery.md         # Module discovery contract
    ├── canonical-commands.md       # Command vocabulary and resolution
    ├── config-callback.md          # Project configuration callback
    ├── triage-extension.md         # Triage extension contract
    ├── outline-extension.md        # Outline extension contract
    ├── verify-steps.md             # Verify steps contract
    ├── recipe-extension.md         # Recipe extension contract
    ├── build-execution.md          # Execution patterns and lifecycle (optional)
    ├── build-return.md             # Return value structure (optional)
    ├── build-project-structure.md  # Module discovery output (optional)
    ├── workflow-overview.md        # 6-phase workflow contract overview
    ├── profile-mechanism.md        # How profile overrides work
    ├── profile-implementation.md   # Implementation profile contract
    ├── profile-module-testing.md   # Module testing profile contract
    └── user-review-protocol.md     # User review gate protocol
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
| `provides_recipes() -> list[dict]` | `[]` | Return available recipe definitions |

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
│  recipe-ext: Predefined repeatable transformations               │
│                            │                                     │
│                            │ loads                               │
│                            ▼                                     │
│  LAYER 4: DOMAIN SKILLS (Loaded from task.skills at execution)  │
│  java-core, java-cdi, junit-core, cui-javascript, etc.           │
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
| [skill-domains.md](standards/skill-domains.md) | Skill domains contract | Implementing `get_skill_domains()` |
| [module-discovery.md](standards/module-discovery.md) | Module discovery contract | Implementing `discover_modules()` |
| [config-callback.md](standards/config-callback.md) | Project configuration callback | Implementing `config_defaults()` |
| [triage-extension.md](standards/triage-extension.md) | Triage extension contract | Implementing `provides_triage()` |
| [outline-extension.md](standards/outline-extension.md) | Outline extension contract | Implementing `provides_outline_skill()` |
| [verify-steps.md](standards/verify-steps.md) | Verify steps contract | Implementing `provides_verify_steps()` |
| [recipe-extension.md](standards/recipe-extension.md) | Recipe extension contract | Implementing `provides_recipes()` |
| [build-execution.md](standards/build-execution.md) | Execution patterns and lifecycle | Running build commands |
| [build-return.md](standards/build-return.md) | Return value structure | Formatting command output |
| [build-project-structure.md](standards/build-project-structure.md) | Module discovery output spec | Understanding `discover_modules()` output format |
| [workflow-overview.md](standards/workflow-overview.md) | 6-phase workflow contract | Understanding phase transitions and contracts |
| [profile-mechanism.md](standards/profile-mechanism.md) | Profile override mechanism | Understanding how domains override profile skills |
| [profile-implementation.md](standards/profile-implementation.md) | Implementation profile contract | Implementing/overriding the implementation profile |
| [profile-module-testing.md](standards/profile-module-testing.md) | Module testing profile contract | Implementing/overriding the module testing profile |
| [user-review-protocol.md](standards/user-review-protocol.md) | User review gate protocol | Understanding mandatory user review after outline |
| orchestrator-integration.md (manage-architecture skill) | Orchestrator merge logic | Understanding hybrid modules |

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

### Build Execution Utilities (Internal)

These are NOT part of the extension API. They are imported directly by build scripts (`build-maven`, `build-npm`, etc.), not through `extension_base`.

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

Scripts can import discovery functions directly:

```python
import sys
from pathlib import Path

# Add extension-api scripts to path
extension_api_path = Path(__file__).parent.parent.parent / "extension-api" / "scripts"
sys.path.insert(0, str(extension_api_path))

from extension_discovery import (
    discover_all_extensions,
    discover_project_modules,
    get_skill_domains_from_extensions,
    apply_config_defaults,
)

from build_discover import (
    discover_descriptors,
    build_module_base,
    find_readme,
)

from build_result import (
    create_log_file,
    success_result,
    error_result,
)

from build_parse import (
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

---

## References

- `standards/extension-contract.md` - Extension API contract (required)
- `standards/skill-domains.md` - Skill domains contract (required)
- `standards/module-discovery.md` - Module discovery contract (required)
- `standards/canonical-commands.md` - Command vocabulary and resolution (required)
- `standards/config-callback.md` - Project configuration callback (required)
- `standards/triage-extension.md` - Triage extension contract (required)
- `standards/outline-extension.md` - Outline extension contract (required)
- `standards/verify-steps.md` - Verify steps contract (required)
- `standards/recipe-extension.md` - Recipe extension contract (required)
- `standards/build-execution.md` - Execution patterns and lifecycle (optional)
