# Extension API Contract

Complete specification for `extension.py` files that domain bundles implement. All extensions **must** inherit from `ExtensionBase`.

## File Location

Extensions are located at:
```
marketplace/bundles/{bundle}/skills/plan-marshall-plugin/extension.py
```

At runtime, they're discovered from the plugin cache:
```
~/.claude/plugins/cache/plan-marshall/{bundle}/1.0.0/skills/plan-marshall-plugin/extension.py
```

---

## ExtensionBase Import

All extensions must import and inherit from `ExtensionBase`:

```python
from extension_base import ExtensionBase

class Extension(ExtensionBase):
    # Implement required methods
    ...
```

The `extension_base` module is automatically injected into `sys.modules` when extensions are loaded.

---

## Required Methods (Abstract)

All extensions must implement these methods - they are abstract in `ExtensionBase`.

### get_skill_domains

```python
def get_skill_domains(self) -> dict:
    """Return domain metadata for skill loading.

    Returns:
        Dict with domain identity and profile-based skill organization:
        {
            "domain": {
                "key": str,          # Unique domain identifier
                "name": str,         # Human-readable name
                "description": str   # Domain description
            },
            "profiles": {
                "core": {
                    "defaults": list[str],    # Always-loaded skills
                    "optionals": list[str]    # On-demand skills
                },
                "implementation": {...},
                "testing": {...},
                "quality": {...}
            }
        }

    Profile Categories:
        - core: Foundation patterns and standards
        - implementation: Runtime patterns (CDI, frameworks)
        - testing: Test frameworks and patterns
        - quality: Documentation, code quality
    """
```

---

## Optional Methods (With Defaults)

These methods have default implementations in `ExtensionBase`. Override only when needed.

### Configuration Callback

#### config_defaults

```python
def config_defaults(self, project_root: str) -> None:
    """Configure project-specific defaults in run-configuration.json.

    Called by marshall-steward during initialization, after extension loading
    but before workflow logic accesses configuration.

    Args:
        project_root: Absolute path to project root directory.

    Returns:
        None (void method)

    Contract:
        - MUST only write values if they don't already exist
        - MUST NOT override user-defined configuration
        - SHOULD use script executor for setting values
        - MAY skip silently if no defaults are needed

    Default: no-op (pass)
    """
```

See [config-callback.md](config-callback.md) for implementation patterns and examples.

### Module Discovery Methods

#### discover_modules (Primary API)

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
```

See [build-project-structure.md](build-project-structure.md) for the complete output specification and implementation patterns.

### Workflow Extension Methods

#### provides_triage

```python
def provides_triage(self) -> str | None:
    """Return triage skill reference if available.

    Returns:
        Skill reference as 'bundle:skill' (e.g., 'pm-dev-java:java-triage')
        or None if no triage capability.

    Default: None
    """
```

#### provides_outline

```python
def provides_outline(self) -> str | None:
    """Return outline skill reference if available.

    Returns:
        Skill reference as 'bundle:skill'
        or None if no outline capability.

    Default: None
    """
```

---

## Canonical Constants

Import `CMD_*` constants from `extension_base` for type-safe command references. See [canonical-commands.md](canonical-commands.md) for the complete vocabulary, resolution logic, and requirements.

---

## Complete Extension Examples

### Minimal Extension (Skill-Only Domain)

```python
#!/usr/bin/env python3
"""Extension API for pm-documents bundle."""

from pathlib import Path
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Documentation extension for pm-documents bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            "domain": {
                "key": "documentation",
                "name": "Documentation",
                "description": "AsciiDoc documentation, ADRs, and interface specifications"
            },
            "profiles": {
                "core": {
                    "defaults": ["pm-documents:cui-documentation"],
                    "optionals": []
                },
                "implementation": {
                    "defaults": [],
                    "optionals": ["pm-documents:adr-management"]
                },
                "testing": {"defaults": [], "optionals": []},
                "quality": {"defaults": [], "optionals": []}
            }
        }
```

### Build Bundle Extension (With Module Discovery)

```python
#!/usr/bin/env python3
"""Extension API for pm-dev-java bundle."""

from pathlib import Path
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Java/Maven extension for pm-dev-java bundle."""

    def get_skill_domains(self) -> dict:
        return {
            "domain": {
                "key": "java",
                "name": "Java Development",
                "description": "Java code patterns, JUnit testing, Maven builds"
            },
            "profiles": {
                "core": {"defaults": ["pm-dev-java:java-core"], "optionals": []},
                "implementation": {"defaults": [], "optionals": []},
                "testing": {"defaults": ["pm-dev-java:junit-core"], "optionals": []},
                "quality": {"defaults": ["pm-dev-java:javadoc"], "optionals": []}
            }
        }

    def provides_triage(self) -> str | None:
        return "pm-dev-java:java-triage"

    def discover_modules(self, project_root: str) -> list:
        # Delegate to script in scripts/ directory
        from maven_cmd_discover import discover_maven_modules
        return discover_maven_modules(project_root)
```

---

## Validation

Extensions are validated by `plugin-doctor extension`:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate extension \
    --extension path/to/extension.py
```

Validation checks:
- Extension class exists and inherits from ExtensionBase
- Required methods implemented (get_skill_domains)
- No syntax errors
- get_skill_domains() returns valid structure with domain.key, domain.name, profiles
- Skill references (bundle:skill) point to existing skills
- Build bundles: discover_modules() returns contract-compliant structure with commands
- provides_triage() and provides_outline() references exist if non-null

---

## Additive Bundles

Some domain bundles are **additive** - they extend a base domain bundle rather than standing alone. Additive bundles:

- Apply **in addition to** a base bundle (both discover modules in the project)
- Do **not** provide their own triage - they rely on the base bundle's triage skill
- Add specialized skills for a subset of projects within the base domain

**Example**: `pm-dev-java-cui` is additive to `pm-dev-java`:
- Applies when pom.xml contains CUI dependencies
- Provides CUI-specific logging/testing skills
- Relies on `pm-dev-java:java-triage` for triage (no `provides_triage()` override)

---

## Existing Extensions

| Bundle | Domain Key | Triage | Outline | Notes |
|--------|------------|--------|---------|-------|
| pm-dev-java | java | java-triage | - | Base Java bundle |
| pm-dev-java-cui | java-cui | - | - | Additive to pm-dev-java |
| pm-dev-frontend | javascript | javascript-triage | - | |
| pm-documents | documentation | documentation-triage | - | |
| pm-requirements | requirements | requirements-triage | - | |
| pm-plugin-development | plan-marshall-plugin-dev | plugin-triage | plugin-solution-outline | |

---

## Related Specifications

- [architecture-overview.md](architecture-overview.md) - System flow and data dependencies
- [config-callback.md](config-callback.md) - Project configuration callback
- [build-execution.md](build-execution.md) - Build command execution API
- [build-return.md](build-return.md) - Build return value structure
- [build-project-structure.md](build-project-structure.md) - Project structure discovery
- [orchestrator-integration.md](../../analyze-project-architecture/standards/orchestrator-integration.md) - Orchestrator flow and hybrid merging
- [canonical-commands.md](canonical-commands.md) - Command vocabulary
