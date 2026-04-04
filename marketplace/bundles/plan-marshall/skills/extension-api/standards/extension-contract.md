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

**Note**: The skill directory name `plan-marshall-plugin` is a convention — `find_extension_path()` in `extension_discovery.py` searches this hardcoded path. All domain bundles must use this directory name for their extension to be discovered.

---

## Skill Directory Convention

Every bundle that provides domain extensions **must** contain a `skills/plan-marshall-plugin/` directory. The `extension_discovery.py` scanner (`find_extension_path()`) looks for this exact path relative to the bundle root:

```
{bundle}/skills/plan-marshall-plugin/extension.py
```

The name `plan-marshall-plugin` is a **convention that signals "this bundle is an extension point for plan-marshall"** — it does NOT mean "a plugin for plan-marshall" or "the plan-marshall plugin." Each bundle's `plan-marshall-plugin` directory contains a different domain-specific extension (Java, Python, OCI, etc.), but the directory name is identical across all bundles so the scanner can discover them uniformly.

### Directory Contents

| File / Directory | Required | Purpose |
|------------------|----------|---------|
| `extension.py` | Yes | Implements `ExtensionBase` — the bundle's domain extension |
| `SKILL.md` | No | Documents the extension's behavior and domain |
| `scripts/` | No | Module discovery logic or other domain-specific scripts |

### Discovery Mechanism

The `find_extension_path()` function in `extension_discovery.py` resolves the extension path using two strategies:

1. **Source structure**: `marketplace/bundles/{bundle}/skills/plan-marshall-plugin/extension.py`
2. **Cache structure** (versioned): `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/skills/plan-marshall-plugin/extension.py`

The path segment `skills/plan-marshall-plugin/extension.py` is hardcoded. Bundles that use a different directory name will not be discovered.

### Bundles Implementing This Convention

All 10 production bundles provide a `skills/plan-marshall-plugin/` directory:

| Bundle | Domain | Description |
|--------|--------|-------------|
| `plan-marshall` | build, general-dev | Core infrastructure and multi-domain extension |
| `pm-dev-java` | java | Java/Maven development patterns and module discovery |
| `pm-dev-java-cui` | java-cui | CUI-specific Java extensions (additive to pm-dev-java) |
| `pm-dev-frontend` | javascript | JavaScript/frontend development standards |
| `pm-dev-frontend-cui` | javascript-cui | CUI-specific JavaScript standards (additive to pm-dev-frontend) |
| `pm-dev-python` | python | Python development standards and build operations |
| `pm-dev-oci` | oci-containers | OCI container standards and security |
| `pm-documents` | documentation | AsciiDoc, ADRs, and interface specifications |
| `pm-plugin-development` | plan-marshall-plugin-dev | Plugin creation and maintenance toolkit |
| `pm-requirements` | requirements | Requirements engineering standards |

### Why the Same Name Everywhere?

A single, fixed directory name enables automatic discovery without configuration. The scanner iterates over all bundle directories and checks for `skills/plan-marshall-plugin/extension.py` — no registry, no manifest lookup, no per-bundle configuration. This makes adding a new domain extension as simple as creating the directory and implementing `ExtensionBase`.

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
- **String format**: `"bundle:skill"` — compact but lacks description for downstream consumers

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

See [Existing Extensions](#existing-extensions) for current implementations.

---

### provides_outline_skill

Declares a domain-specific outline skill with change-type routing for solution outline creation. The skill provides `standards/change-{type}.md` files with domain-specific discovery, analysis, and deliverable logic.

**Lifecycle**: Called during `skill-domains configure`. Stored in `marshal.json` and resolved at runtime by phase-3-outline.

```
Extension discovery → get_skill_domains() → ➤ provides_outline_skill() → stored in marshal.json → resolved by phase-3-outline
```

```python
def provides_outline_skill(self) -> str | None:
    """Return domain-specific outline skill reference as 'bundle:skill', or None.

    Fallback: If None, generic plan-marshall:phase-3-outline
    standards are used.

    Default: None
    """
```

#### Skill Structure Convention

```
{bundle}/skills/{skill}/
├── SKILL.md                       # Shared workflow steps
└── standards/
    └── change-types.md            # All change types (bug_fix, enhancement, feature, tech_debt)
```

| Change Type | Description |
|-------------|-------------|
| `feature` | New functionality or component |
| `enhancement` | Improve existing functionality |
| `bug_fix` | Fix a defect or issue |
| `tech_debt` | Refactoring, cleanup, removal |
| `analysis` | Investigate, research, understand |
| `verification` | Validate, check, confirm |

Not all change types need coverage — unsupported types fall back to `plan-marshall:phase-3-outline/standards/change-{type}.md`.

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

See [Existing Extensions](#existing-extensions) for current implementations. All other domains return `None` and use the generic `plan-marshall:phase-3-outline` standards.

---

### provides_recipes

Declares predefined, repeatable transformations (recipes) that bypass change-type detection and provide their own discovery, analysis, and deliverable patterns. Recipes are presented to users via `/plan-marshall action=recipe`.

**Lifecycle**: Called during `skill-domains configure`. Recipes are discovered at runtime by `list-recipes` and `resolve-recipe` commands.

```
Extension discovery → get_skill_domains() → ➤ provides_recipes() → discovered at runtime by manage-config list-recipes/resolve-recipe
```

```python
def provides_recipes(self) -> list[dict]:
    """Return recipe definitions this extension provides.

    Each recipe dict contains:
        - key: str — Unique recipe identifier (e.g., 'refactor-to-profile-standards')
        - name: str — Human-readable display name
        - description: str — Description for recipe selection UI
        - skill: str — Fully-qualified skill reference ('bundle:recipe-skill')
        - default_change_type: str — Change type for outline phase (e.g., 'tech_debt')
        - scope: str — Scope indicator ('codebase_wide', 'module')

    Optional fields (set by user at plan creation time if omitted):
        - profile: str — Target profile ('implementation', 'module_testing')
        - package_source: str — Package source ('packages', 'test_packages')

    Default: []
    """
```

#### Return Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | str | Yes | Unique recipe identifier — used in `resolve-recipe --recipe {key}` |
| `name` | str | Yes | Human-readable display name for UI |
| `description` | str | Yes | Description shown during recipe selection |
| `skill` | str | Yes | Fully-qualified skill reference (`bundle:recipe-skill`) |
| `default_change_type` | str | Yes | Change type for phase-3-outline (e.g., `tech_debt`, `feature`) |
| `scope` | str | Yes | Scope indicator (`codebase_wide`, `module`) |
| `profile` | str | No | Target profile — omit if user selects at plan creation time |
| `package_source` | str | No | Package source — omit if user selects at plan creation time |

#### Auto-Assigned Fields

The following fields are added automatically by `_discover_all_recipes()` — do **not** include them in the return value:

| Field | Value | Source |
|-------|-------|--------|
| `domain` | First domain key from `get_skill_domains()` | Auto-extracted |
| `source` | `'extension'` | Auto-assigned |

#### Recipe Discovery Sources

Recipes are discovered from two sources (in order):

1. **Extension `provides_recipes()`** — domain bundle recipes (source: `extension`)
2. **Project `recipe-*` skills in `.claude/skills/`** — project-level recipes (source: `project`)

#### Resolution Commands

```bash
# List all recipes from all sources
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-recipes

# Resolve a specific recipe by key
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-recipe --recipe refactor-to-profile-standards
```

#### Recipe Skill Interface

The referenced recipe skill is loaded by phase-3-outline (Step 2.5) with these inputs:

| Parameter | Source |
|-----------|--------|
| `plan_id` | Current plan |
| `recipe_domain` | From status metadata (user-selected or recipe-declared) |
| `recipe_profile` | From status metadata (user-selected or recipe-declared) |
| `recipe_package_source` | From status metadata (user-selected or recipe-declared) |

The recipe skill must write `solution_outline.md` with deliverables grouped by module.

#### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_recipes(self) -> list[dict]:
        return [
            {
                'key': 'refactor-to-profile-standards',
                'name': 'Refactor to Profile Standards',
                'description': 'Refactor code to comply with configured profile standards, package by package',
                'skill': 'plan-marshall:recipe-refactor-to-profile-standards',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
                # profile and package_source omitted — user selects at plan creation
            },
        ]
```

See [Existing Extensions](#existing-extensions) for current implementations.

---

### provides_verify_steps

Declares domain-specific verification agents that run after implementation tasks complete. Steps are appended to the flat `steps` list in `plan.phase-5-execute.steps`.

**Lifecycle**: Called during `skill-domains configure`. Steps appended to `marshal.json` steps list and consumed by phase-4-plan to create holistic verification tasks.

```
Extension discovery → get_skill_domains() → ➤ provides_verify_steps() → appended to steps list → phase-4-plan creates tasks → phase-5-execute runs agents
```

```python
def provides_verify_steps(self) -> list[dict]:
    """Return domain-specific verification steps.

    Each step dict contains:
        - name: Fully-qualified skill reference (e.g., 'my-bundle:my-verify-step')
        - skill: Same as name (the fully-qualified skill reference)
        - description: Human-readable description for wizard presentation

    Default: []
    """
```

#### Return Structure

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Fully-qualified skill reference (`bundle:skill`) — used directly in steps list |
| `skill` | str | Same as name (the fully-qualified skill reference) |
| `description` | str | Human-readable description for `/marshall-steward` wizard |

#### Storage in marshal.json

Extension steps are appended to the flat `plan.phase-5-execute.steps` list after built-in steps:

```json
{
  "plan": {
    "phase-5-execute": {
      "steps": [
        "quality_check",
        "build_verify",
        "coverage_check"
      ]
    }
  }
}
```

Built-in steps (`quality_check`, `build_verify`) are always first. Extension steps follow in discovery order.

#### Manage Commands

```bash
# Add a verify step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute add-step --step my-bundle:my-verify-step

# Remove a verify step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute remove-step --step my-bundle:my-verify-step

# Replace entire steps list
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps quality_check,build_verify

# List all available verify steps (built-in + extensions)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```

#### Runtime Consumption

Phase-4-plan reads the steps list and creates holistic verification tasks:

1. Read config: `plan phase-5-execute get --field steps --trace-plan-id {plan_id}`
2. For each step: create a verification task with `profile: verification`, `deliverable: 0`, `origin: holistic`, `depends_on: [ALL non-holistic tasks]`
3. Built-in steps (`quality_check`, `build_verify`) resolve via architecture commands
4. Extension steps (colon notation) use the step name directly as the agent reference

#### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_verify_steps(self) -> list[dict]:
        return [
            {
                'name': 'my-bundle:my-verify-step',
                'skill': 'my-bundle:my-verify-step',
                'description': 'Custom domain verification',
            },
        ]
```

No bundles currently provide verification steps. See [Existing Extensions](#existing-extensions) for the full matrix.

> **Note**: Coverage verification is handled by the built-in `default:coverage_check` step, not by an extension agent. See the dispatch table in `phase-5-execute`.

---

### provides_finalize_steps

Declares domain-specific finalize steps that execute during the phase-6-finalize pipeline. Steps are discovered by marshall-steward and presented to the user for selection.

**Lifecycle**: Called during step discovery (marshall-steward wizard/menu). Selected steps are added to the `steps` list in `marshal.json` under `plan.phase-6-finalize.steps`.

```
Extension discovery → ➤ provides_finalize_steps() → marshall-steward multi-select → stored in marshal.json steps list → phase-6-finalize dispatches via Skill:
```

```python
def provides_finalize_steps(self) -> list[dict]:
    """Return domain-specific finalize steps.

    Each step dict contains:
        - name: str — Fully-qualified skill notation (used as step reference in steps list)
        - skill: str — Same as name (fully-qualified skill reference)
        - description: str — Human-readable description for wizard presentation

    Default: []
    """
```

#### Return Structure

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Fully-qualified skill notation — used as step reference in `steps` list |
| `skill` | str | Same as `name` (the skill to invoke) |
| `description` | str | Human-readable description for `/marshall-steward` wizard |

#### Storage in marshal.json

Extension-contributed steps are added to the ordered `steps` list:

```json
{
  "plan": {
    "phase-6-finalize": {
      "steps": [
        "commit_push",
        "create_pr",
        "pm-dev-java:java-post-pr",
        "branch_cleanup",
        "archive"
      ]
    }
  }
}
```

The step reference is the fully-qualified skill notation. The position in the list determines execution order.

#### Interface Contract

Each finalize step skill receives:

| Parameter | Description |
|-----------|-------------|
| `--plan-id` | The plan being finalized |
| `--iteration` | Current finalize iteration (1-based) |

The step skill can access plan context via manage-* scripts.

#### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_finalize_steps(self) -> list[dict]:
        return [
            {
                'name': 'pm-dev-java:java-post-pr',
                'skill': 'pm-dev-java:java-post-pr',
                'description': 'Java post-PR validation and artifact publishing',
            },
        ]
```

No bundles currently provide finalize steps. See [Existing Extensions](#existing-extensions) for the full matrix.

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
        return []  # Coverage is now a built-in verify step (default:coverage_check)

    def discover_modules(self, project_root: str) -> list:
        # Delegate to script in scripts/ directory
        from _maven_cmd_discover import discover_maven_modules
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

> **Note**: This table is a reference snapshot. For the authoritative live list, use `extension_discovery discover-all`.

| Bundle | Domain Key | Triage | Outline Skill | Recipes | Verify Steps | Notes |
|--------|------------|--------|---------------|---------|-------------|-------|
| pm-dev-java | java | ext-triage-java | - | - | - | Base Java bundle |
| pm-dev-java-cui | java-cui | - | - | - | - | Additive to pm-dev-java |
| pm-dev-frontend | javascript | ext-triage-js | - | - | - | |
| pm-dev-python | python | ext-triage-python | - | - | - | |
| pm-dev-oci | oci-containers | ext-triage-oci | - | - | - | |
| pm-documents | documentation | ext-triage-docs | - | - | - | Uses recipe for doc verification |
| pm-requirements | requirements | ext-triage-reqs | - | - | - | |
| pm-plugin-development | plan-marshall-plugin-dev | ext-triage-plugin | ext-outline-workflow | - | - | |
| plan-marshall | build, general-dev | - | - | 1 (refactor-to-profile-standards) | - | Multi-domain |

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

### Why Six Optional Hooks?

All six hooks (config_defaults, provides_triage, provides_outline_skill, provides_recipes, provides_verify_steps, provides_finalize_steps) follow the same extension model:

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
