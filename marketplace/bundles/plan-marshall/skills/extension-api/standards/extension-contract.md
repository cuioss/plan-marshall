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

The `extension_base` module is available via PYTHONPATH set by the executor.

---

## Required Methods (Abstract)

All extensions must implement these methods - they are abstract in `ExtensionBase`.

### get_skill_domains

Defines the extension's domain identity and organizes skills into profiles for context-appropriate loading. This is the only **required** (abstract) method in `ExtensionBase`.

**Lifecycle**: Called during `/marshall-steward` domain configuration (`skill-domains configure`). The returned structure defines the domain's identity and skill organization for the entire planning lifecycle.

```
1. Extension discovery and loading
2. ➤ get_skill_domains() → domain metadata + skill profiles
3. Domain registered in marshal.json under skill_domains.{domain_key}
4. Profiles consumed by phase skills to load domain-specific knowledge
```

```python
def get_skill_domains(self) -> list[dict]:
    """Return all skill domains this extension provides.

    Returns:
        List of domain dicts. Each dict has domain identity and
        profile-based skill organization:
        [{
            "domain": {
                "key": str,          # Unique domain identifier
                "name": str,         # Human-readable name
                "description": str   # Domain description
            },
            "profiles": {
                "core": {
                    "defaults": list[dict|str],  # Always-loaded skills (prefer object format)
                    "optionals": list[dict|str]  # On-demand skills
                },
                "implementation": {...},
                "module_testing": {...},
                "quality": {...}
            }
        }]

    Most extensions return a single-element list. Multi-domain
    extensions (e.g., plan-marshall) return multiple elements.

    This method is abstract — all extensions MUST implement it.
    """
```

#### Domain Object

| Field | Type | Description |
|-------|------|-------------|
| `domain.key` | str | Unique domain identifier (e.g., `java`, `javascript`, `documentation`) |
| `domain.name` | str | Human-readable name (e.g., `Java Development`) |
| `domain.description` | str | Domain description for display |

#### Profiles Map

Each profile contains `defaults` (always loaded) and `optionals` (loaded on demand):

| Profile | Purpose | When Loaded |
|---------|---------|-------------|
| `core` | Foundation patterns and standards | Always — base knowledge for the domain |
| `implementation` | Runtime patterns (CDI, frameworks) | During implementation tasks |
| `module_testing` | Test frameworks and patterns | During unit/module testing tasks |
| `integration_testing` | Integration test patterns | During integration testing tasks |
| `quality` | Documentation, code quality standards | During quality and verification tasks |
| `documentation` | Documentation-specific standards (optional) | Domain-specific extra profile |

**Skill Reference Format**: Each skill entry can be either:
- **Object format** (preferred): `{"skill": "bundle:skill", "description": "What this skill provides"}` — self-documenting, enables validation
- **String format** (legacy): `"bundle:skill"` — compact but lacks description for downstream consumers

Object format is preferred for new extensions. Both formats are accepted by `_build_applicable_result()` and the enrichment pipeline.

#### Defaults vs Optionals

- **defaults**: Skills loaded automatically when the profile is activated
- **optionals**: Skills available for on-demand loading when specific knowledge is needed

#### Storage in marshal.json

The returned structure is stored in `marshal.json` under `skill_domains.{domain_key}`:

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "outline_skill": null,
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  }
}
```

The `bundle` field is a **reverse mapping** added automatically by `skill-domains configure` — it records which bundle provides this domain. Since domain keys (e.g., `java`) differ from bundle names (e.g., `pm-dev-java`), this field is needed to locate the source `extension.py` for runtime operations.

#### Validation

- `get_skill_domains()` returns valid structure with `domain.key`, `domain.name`, `profiles`
- Required profiles exist (`core`, `implementation`, `module_testing`, `quality`)
- Each profile has `defaults` and `optionals` lists
- Skill references (`bundle:skill`) point to existing registered skills

---

## Optional Methods (With Defaults)

These methods have default implementations in `ExtensionBase`. Override only when needed.

### config_defaults

Sets project-specific configuration defaults in `marshal.json` before other components access them. Enables domain-specific defaults, project-aware configuration, and user-overridable settings.

**Lifecycle**: Called after extensions are loaded but before any workflow logic accesses configuration.

```
Extension discovery → load → ➤ config_defaults() → plugin access / workflow execution
```

```python
def config_defaults(self, project_root: str) -> None:
    """Configure project-specific defaults in marshal.json.

    Args:
        project_root: Absolute path to project root directory.

    Returns:
        None (void method)

    Contract:
        - MUST only write values if they don't already exist (write-once)
        - MUST NOT override user-defined configuration
        - SHOULD use direct import from _config_core module
        - MAY skip silently if no defaults are needed

    Default: no-op (pass)
    """
```

#### Write-Once Semantics

The critical contract: **only write if the key doesn't exist**. The `extension-defaults set-default` command implements this automatically.

#### Implementation Pattern

**Recommended** — direct import:

```python
from _config_core import ext_defaults_set_default

class Extension(ExtensionBase):
    def config_defaults(self, project_root: str) -> None:
        ext_defaults_set_default("build.maven.profiles.skip", "itest,native", project_root)
        ext_defaults_set_default("build.maven.profiles.map.canonical", "pre-commit:quality-gate", project_root)
```

**Alternative** — CLI via subprocess:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ext-defaults set-default \
  --key "my_bundle.my_setting" --value "default_value"
```

#### Available Operations

| Operation | Description |
|-----------|-------------|
| `ext-defaults set-default` | Set value only if key doesn't exist (write-once) |
| `ext-defaults get/set/list/remove` | Generic key-value operations in `extension_defaults` |

---

### discover_modules (Primary API)

```python
def discover_modules(self, project_root: str) -> list:
    """Discover all modules with complete metadata.

    This is the primary API for module discovery. Returns comprehensive
    module information including metadata, dependencies, packages, and stats.

    Args:
        project_root: Absolute path to project root.

    Returns:
        List of module dicts. See module-discovery.md for complete
        output structure including paths, metadata, packages, dependencies,
        stats, and commands fields.

    Default: []
    """
```

See [module-discovery.md](module-discovery.md) for the method contract and complete output specification.

---

### provides_triage

Declares a domain-specific triage skill containing finding decision-making knowledge — suppression syntax, severity guidelines, and acceptable-to-accept criteria.

**Lifecycle**: Called during `skill-domains configure`. Stored in `marshal.json` and resolved at runtime when findings need triage.

```
Extension discovery → get_skill_domains() → ➤ provides_triage() → stored in marshal.json → resolved by execute/finalize phases
```

```python
def provides_triage(self) -> str | None:
    """Return triage skill reference as 'bundle:skill', or None.

    Default: None
    """
```

#### Required Skill Sections

The referenced triage skill MUST include:

| Section | Purpose | Content |
|---------|---------|---------|
| `## Suppression Syntax` | How to suppress findings | Annotation/comment syntax per finding type |
| `## Severity Guidelines` | When to fix vs suppress vs accept | Decision table by severity |
| `## Acceptable to Accept` | What can be accepted without fixing | Situations where accepting is appropriate |

#### Triage Decision Flow

```
1. Run verification (build, test, lint, Sonar)
2. Collect findings
3. For each finding:
   a. Determine domain from file path/extension
   b. resolve-workflow-skill-extension --domain {domain} --type triage
   c. If extension exists: load skill, apply severity/suppression rules
   d. If no extension: use default severity mapping
   e. Decide: fix | suppress | accept
4. Apply fixes/suppressions → re-run verification if changes made
```

#### Storage in marshal.json

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  }
}
```

#### Resolution Command

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain java --type triage
```

#### Existing Implementations

| Bundle | Domain | Triage Skill |
|--------|--------|-------------|
| pm-dev-java | java | `pm-dev-java:ext-triage-java` |
| pm-dev-frontend | javascript | `pm-dev-frontend:ext-triage-js` |
| pm-documents | documentation | `pm-documents:ext-triage-docs` |
| pm-requirements | requirements | `pm-requirements:ext-triage-reqs` |
| pm-plugin-development | plan-marshall-plugin-dev | `pm-plugin-development:ext-triage-plugin` |

Bundles without triage (returns `None`): pm-dev-java-cui (relies on base bundle).

---

### provides_outline_skill

Declares a domain-specific outline skill with change-type routing for solution outline creation. The skill provides `standards/change-{type}.md` files with domain-specific discovery, analysis, and deliverable logic.

**Lifecycle**: Called during `skill-domains configure`. Stored in `marshal.json` and resolved at runtime by phase-3-outline.

```
Extension discovery → get_skill_domains() → ➤ provides_outline_skill() → stored in marshal.json → resolved by workflow-outline-change-type
```

```python
def provides_outline_skill(self) -> str | None:
    """Return domain-specific outline skill reference as 'bundle:skill', or None.

    Fallback: If None, generic plan-marshall:workflow-outline-change-type
    standards are used.

    Default: None
    """
```

#### Skill Structure Convention

```
{bundle}/skills/{skill}/
├── SKILL.md                       # Shared workflow steps
└── standards/
    ├── change-feature.md          # Create new components
    ├── change-enhancement.md      # Improve existing components
    ├── change-bug_fix.md          # Fix component bugs
    └── change-tech_debt.md        # Refactor/cleanup
```

| Change Type | Description |
|-------------|-------------|
| `feature` | New functionality or component |
| `enhancement` | Improve existing functionality |
| `bug_fix` | Fix a defect or issue |
| `tech_debt` | Refactoring, cleanup, removal |
| `analysis` | Investigate, research, understand |
| `verification` | Validate, check, confirm |

Not all change types need coverage — unsupported types fall back to `plan-marshall:workflow-outline-change-type/standards/change-{type}.md`.

#### Storage in marshal.json

The outline skill reference is stored at the domain level (not inside `workflow_skill_extensions`):

```json
{
  "skill_domains": {
    "plan-marshall-plugin-dev": {
      "bundle": "pm-plugin-development",
      "outline_skill": "pm-plugin-development:ext-outline-workflow",
      "workflow_skill_extensions": {
        "triage": "pm-plugin-development:ext-triage-plugin"
      }
    }
  }
}
```

#### Resolution Command

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-outline-skill --domain plan-marshall-plugin-dev
```

Returns `source: domain_specific` when a custom skill exists, or `source: generic_fallback` when using defaults.

#### Existing Implementations

| Bundle | Domain | Outline Skill |
|--------|--------|--------------|
| pm-plugin-development | plan-marshall-plugin-dev | `pm-plugin-development:ext-outline-workflow` |

All other domains return `None` and use the generic `plan-marshall:workflow-outline-change-type` standards.

---

### provides_verify_steps

Declares domain-specific verification agents that run after implementation tasks complete. Steps are user-configurable (enable/disable per step).

**Lifecycle**: Called during `skill-domains configure`. Steps stored in `marshal.json` and consumed by phase-4-plan to create holistic verification tasks.

```
Extension discovery → get_skill_domains() → ➤ provides_verify_steps() → stored in marshal.json → phase-4-plan creates tasks → phase-5-execute runs agents
```

```python
def provides_verify_steps(self) -> list[dict]:
    """Return domain-specific verification steps.

    Each step dict contains:
        - name: Step identifier (e.g., 'technical_impl')
        - agent: Fully-qualified agent reference ('bundle:agent')
        - description: Human-readable description for wizard presentation

    Default: []
    """
```

#### Return Structure

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Step identifier — used as key suffix in marshal.json |
| `agent` | str | Fully-qualified agent reference (`bundle:agent`) |
| `description` | str | Human-readable description for `/marshall-steward` wizard |

#### Storage in marshal.json

Stored under `plan.phase-5-execute.verification_domain_steps.{domain_key}` with numbered keys:

```json
{
  "plan": {
    "phase-5-execute": {
      "verification_domain_steps": {
        "java": {
          "1_technical_impl": "pm-dev-java:java-verify-agent",
          "2_technical_test": "pm-dev-java:java-coverage-agent"
        },
        "documentation": {
          "1_doc_sync": "pm-documents:doc-verify"
        }
      }
    }
  }
}
```

Key format: `{number}_{step_name}`. Value: agent reference string, or `false` to disable.

#### Enable/Disable Commands

```bash
# Disable a step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-domain-step --domain java --step 1_technical_impl --enabled false

# Change the agent for a step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-domain-step-agent --domain java --step 1_technical_impl --agent pm-dev-java:java-verify-agent
```

#### Runtime Consumption

Phase-4-plan reads the stored configuration and creates holistic verification tasks:

1. Read config: `plan phase-5-execute get --trace-plan-id {plan_id}`
2. For each enabled domain step: create a verification task with `profile: verification`, `deliverable: 0`, `origin: holistic`, `depends_on: [ALL non-holistic tasks]`
3. Tasks invoke the declared agent during phase-5-execute

#### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_verify_steps(self) -> list[dict]:
        return [
            {
                'name': 'technical_impl',
                'agent': 'pm-dev-java:java-verify-agent',
                'description': 'Verify implementation standards compliance',
            },
            {
                'name': 'technical_test',
                'agent': 'pm-dev-java:java-coverage-agent',
                'description': 'Verify test coverage meets thresholds',
            },
        ]
```

#### Existing Implementations

| Bundle | Domain | Steps | Details |
|--------|--------|-------|---------|
| pm-dev-java | java | 2 | `technical_impl` (java-verify-agent), `technical_test` (java-coverage-agent) |
| pm-documents | documentation | 1 | `doc_sync` (doc-verify) |
| pm-requirements | requirements | 1 | `formal_spec` (spec-verify) |

Bundles without verification steps (returns `[]`): pm-dev-frontend, pm-dev-java-cui, pm-plugin-development.

---

### applies_to_module

```python
def applies_to_module(self, module_data: dict,
                      active_profiles: set[str] | None = None) -> dict:
    """Check if this domain applies to a specific module and return resolved skills.

    Called during architecture enrichment to determine which skill domains
    apply to a module and what skills they provide.

    Args:
        module_data: Module dict from derived-data.json
        active_profiles: Optional positive list of profiles to include

    Returns:
        {
            'applicable': bool,
            'confidence': 'high' | 'medium' | 'low' | 'none',
            'signals': list[str],
            'additive_to': str | None,
            'skills_by_profile': {...}  # only when applicable
        }

    Default: returns not applicable.
    """
```

### Protected Helpers

#### _detect_applicable_profiles

```python
def _detect_applicable_profiles(self, profiles: dict,
                                 module_data: dict | None) -> set[str] | None:
    """Detect which profiles are applicable based on module signals.

    Returns set of applicable profile names, or None for no filtering
    (all defined profiles are included). Override in domain extensions
    for signal-based detection.

    Default: None (no filtering)
    """
```

---

## Build Execution Utilities (Co-Located, Not Part of Extension API)

The `_build_result.py`, `_build_parse.py`, `_build_format.py`, and `_build_wrapper.py` scripts are co-located in the `extension-api/scripts/` directory for PYTHONPATH convenience but are **not** part of the extension API. They are internal utilities imported directly by build scripts (e.g., `build-maven`, `build-npm`), not through `ExtensionBase`. Extension implementers do not need to use them.

They are co-located here because:
1. The executor adds `extension-api/scripts/` to PYTHONPATH for all extensions
2. Build scripts need these utilities and already have this path available
3. Moving them would require a separate PYTHONPATH entry with no functional benefit

See [build-execution.md](build-execution.md) for the build execution API specification.

---

## Canonical Constants

Import `CMD_*` constants from `extension_base` for type-safe command references. See [canonical-commands.md](canonical-commands.md) for the complete vocabulary, resolution logic, and requirements.

---

## Complete Extension Examples

### Minimal Extension (Skill-Only Domain)

```python
#!/usr/bin/env python3
"""Extension API for pm-documents bundle."""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Documentation extension for pm-documents bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [{
            "domain": {
                "key": "documentation",
                "name": "Documentation",
                "description": "AsciiDoc documentation, ADRs, and interface specifications"
            },
            "profiles": {
                "core": {
                    "defaults": [
                        {"skill": "pm-documents:ref-asciidoc", "description": "AsciiDoc formatting and validation"},
                        {"skill": "pm-documents:ref-documentation", "description": "Content quality and review"},
                    ],
                    "optionals": []
                },
                "implementation": {
                    "defaults": [],
                    "optionals": [
                        {"skill": "pm-documents:manage-adr", "description": "ADR creation and management"},
                    ]
                },
                "module_testing": {"defaults": [], "optionals": []},
                "quality": {"defaults": [], "optionals": []}
            }
        }]
```

### Build Bundle Extension (With Module Discovery)

```python
#!/usr/bin/env python3
"""Extension API for pm-dev-java bundle."""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Java/Maven extension for pm-dev-java bundle."""

    def get_skill_domains(self) -> list[dict]:
        return [{
            "domain": {
                "key": "java",
                "name": "Java Development",
                "description": "Java code patterns, JUnit testing, Maven builds"
            },
            "profiles": {
                "core": {
                    "defaults": [
                        {"skill": "pm-dev-java:java-core", "description": "Core Java patterns and standards"},
                    ],
                    "optionals": []
                },
                "implementation": {"defaults": [], "optionals": []},
                "module_testing": {
                    "defaults": [
                        {"skill": "pm-dev-java:junit-core", "description": "JUnit 5 testing patterns"},
                    ],
                    "optionals": []
                },
                "quality": {
                    "defaults": [
                        {"skill": "pm-dev-java:javadoc", "description": "JavaDoc documentation standards"},
                    ],
                    "optionals": []
                }
            }
        }]

    def provides_triage(self) -> str | None:
        return "pm-dev-java:ext-triage-java"

    def provides_verify_steps(self) -> list[dict]:
        return [
            {
                'name': 'technical_impl',
                'agent': 'pm-dev-java:java-verify-agent',
                'description': 'Verify implementation standards compliance',
            },
        ]

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
- Required profiles exist (core, implementation, module_testing, quality)
- Each profile has defaults and optionals lists
- Skill references (bundle:skill) point to existing skills
- Build bundles: discover_modules() returns contract-compliant structure with commands
- provides_triage() references exist if non-null
- provides_outline_skill() skill reference exists if non-null

---

## Additive Bundles

Some domain bundles are **additive** - they extend a base domain bundle rather than standing alone. Additive bundles:

- Apply **in addition to** a base bundle (both discover modules in the project)
- Do **not** provide their own triage - they rely on the base bundle's triage skill
- Add specialized skills for a subset of projects within the base domain

**Example**: `pm-dev-java-cui` is additive to `pm-dev-java`:
- Applies when pom.xml contains CUI dependencies
- Provides CUI-specific logging/testing skills
- Relies on `pm-dev-java:ext-triage-java` for triage (no `provides_triage()` override)

---

## Existing Extensions

| Bundle | Domain Key | Triage | Outline Skill | Verify Steps | Notes |
|--------|------------|--------|---------------|-------------|-------|
| pm-dev-java | java | ext-triage-java | - | 2 (impl, test) | Base Java bundle |
| pm-dev-java-cui | java-cui | - | - | - | Additive to pm-dev-java |
| pm-dev-frontend | javascript | ext-triage-js | - | - | |
| pm-dev-python | python | - | - | - | |
| pm-dev-oci | oci-containers | - | - | - | |
| pm-documents | documentation | ext-triage-docs | - | 1 (doc_sync) | Uses generic skills |
| pm-requirements | requirements | ext-triage-reqs | - | 1 (formal_spec) | |
| pm-plugin-development | plan-marshall-plugin-dev | ext-triage-plugin | ext-outline-workflow | - | |
| plan-marshall | build, general-dev | - | - | - | Multi-domain |

---

## Design Rationale

### Why Profile-Based?

Profiles organize skills by usage context rather than flat lists because:

1. **Context-appropriate loading** — implementation tasks don't need testing standards
2. **Performance** — only load skills needed for the current task profile
3. **Clarity** — clear purpose for each skill in the domain

### Why get_skill_domains Required?

This is the only abstract method because every domain must:

1. **Declare identity** — the domain key is used throughout marshal.json
2. **Provide skills** — skills are the primary value a domain extension contributes

### Why Four Optional Hooks?

All four hooks (config_defaults, provides_triage, provides_outline_skill, provides_verify_steps) follow the same extension model:

1. **Domain ownership** — each domain declares its own capabilities rather than core code hardcoding domain-specific behavior
2. **Safe defaults** — all hooks return None or empty, so bundles only implement what they need
3. **Discoverability** — `/marshall-steward` exposes all available hooks during configuration
4. **Separation of concerns** — workflow skills own the process, extension skills own domain knowledge
5. **User override** — configuration is persisted in `marshal.json` where users can inspect and modify it

---

## Related Specifications

- [module-discovery.md](module-discovery.md) - Module discovery contract and output specification
- [canonical-commands.md](canonical-commands.md) - Command vocabulary
- [build-execution.md](build-execution.md) - Build command execution API and return structure
- [profiles.md](profiles.md) - Profile override mechanism and profile contracts
- [workflow-overview.md](workflow-overview.md) - 6-phase workflow and user review gate
