# Extension API Contract

Complete specification for `extension.py` files that domain bundles implement. All extensions **must** inherit from `ExtensionBase`.

## File Location

Extensions are located at:
```text
marketplace/bundles/{bundle}/skills/plan-marshall-plugin/extension.py
```

At runtime, they're discovered from the plugin cache:
```text
~/.claude/plugins/cache/plan-marshall/{bundle}/1.0.0/skills/plan-marshall-plugin/extension.py
```

**Note**: Bundles conventionally place the manifest under `skills/plan-marshall-plugin/`, but the directory name is **not** the discovery key. `find_extension_path()` in `extension_discovery.py` discovers the manifest by reading the `implements:` frontmatter declaration from each candidate `skills/*/SKILL.md` and derives the sibling `extension.py` from the matched manifest's directory. See [ext-point-domain-bundle.md](ext-point-domain-bundle.md) for the manifest archetype contract.

---

## Skill Directory Convention

Every bundle that provides domain extensions **must** ship a domain-bundle manifest skill whose `SKILL.md` declares:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-domain-bundle
```

The manifest skill conventionally lives at `skills/plan-marshall-plugin/`, with the bundle's `extension.py` as its sibling:

```text
{bundle}/skills/plan-marshall-plugin/extension.py
```

The directory name `plan-marshall-plugin` is a **convention that reads "this bundle is an extension point for plan-marshall"** — it does NOT mean "a plugin for plan-marshall" or "the plan-marshall plugin." Each bundle's manifest contains a different domain-specific extension (Java, Python, OCI, etc.). The scanner discovers each manifest uniformly through its `implements:` frontmatter declaration — the directory name is conventional, not load-bearing.

### Directory Contents

| File / Directory | Required | Purpose |
|------------------|----------|---------|
| `extension.py` | Yes | Implements `ExtensionBase` — the bundle's domain extension |
| `SKILL.md` | No | Documents the extension's behavior and domain |
| `scripts/` | No | Module discovery logic or other domain-specific scripts |

### Discovery Mechanism

The `find_extension_path()` function in `extension_discovery.py` discovers the manifest by scanning each bundle's candidate `skills/*/SKILL.md` files for the `implements:` frontmatter declaration and deriving the sibling `extension.py` from the matched manifest's directory. It resolves across two structures:

1. **Source structure**: `marketplace/bundles/{bundle}/skills/*/SKILL.md`
2. **Cache structure** (versioned): `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/skills/*/SKILL.md`

Discovery is keyed on the `implements: plan-marshall:extension-api/standards/ext-point-domain-bundle` declaration, not on a directory-name path literal. A bundle whose manifest `SKILL.md` omits the declaration is not discovered, regardless of its directory name. See [ext-point-domain-bundle.md](ext-point-domain-bundle.md) for the archetype-identification contract.

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

The shared `plan-marshall-plugin` directory name is a readability convention so every bundle's manifest is found in the same place by a human. Automatic discovery does not depend on it: the scanner iterates over all bundle directories and selects the `SKILL.md` whose frontmatter declares `implements: plan-marshall:extension-api/standards/ext-point-domain-bundle` — no registry, no per-bundle configuration. This makes adding a new domain extension as simple as creating the manifest skill, declaring the `implements:` key, and implementing `ExtensionBase`.

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

```text
1. Extension discovery and loading
2. -> get_skill_domains() -> domain metadata + skill profiles
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

```text
Extension discovery -> load -> -> config_defaults() -> plugin access / workflow execution
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

### provides_arch_gate

Declares this domain's native architectural-constraint tool for the `arch-gate` canonical command. Optional additive hook mirroring `provides_triage()` / `provides_outline_skill()`: returns a descriptor naming the tool, or `None` (the default) when the domain provides no arch-gate.

**Lifecycle**: Called by `skill-domains configure` for each configured domain. When any configured domain's extension returns a non-None descriptor, `configure` appends the `default:verify:arch-gate` per-deliverable read-only verify-step to `phase-5-execute.verification_steps`. Domains returning `None` append nothing — the silent-skip default.

```python
def provides_arch_gate(self) -> dict | None:
    """Return this domain's arch-gate tool descriptor, or None.

    Returns:
        A descriptor dict ``{'tool': str}`` naming the native architectural-
        constraint tool (e.g. ``{'tool': 'archunit'}`` for Java,
        ``{'tool': 'import-linter'}`` for Python,
        ``{'tool': 'dependency-cruiser'}`` for JavaScript), or None when the
        domain provides no arch-gate.

    Default: None
    """
```

**Single execution model**: There is exactly one arch-gate execution mode — a per-deliverable read-only verify-step that resolves through `architecture resolve --command arch-gate` and runs the domain's native tool as a structural-boundary gate, parsing its output into `arch-constraint`-typed findings (see [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md)). The descriptor carries only the tool name — there is no `execution_mode` key and no piggyback-on-module-tests variant. The single authoritative model for the structural concept lives in [`manage-architecture/standards/arch-gate-fitness-functions.md`](../../manage-architecture/standards/arch-gate-fitness-functions.md); `default:verify:arch-gate` is the domain-appended verify-step described in [`ext-point-build-verify-step.md`](ext-point-build-verify-step.md) § Domain-Appended Verify Steps.

---

### provides_domain_verb

Declares a domain-owned executable verb — a domain-contributed *command* (a script or resolvable notation) that core dispatches through the resolved notation when the domain is active, and resolves null-on-absent when it is not. Optional additive hook mirroring `provides_arch_gate()`'s descriptor-or-None shape; it is the executable-capability sibling of the knowledge-contribution hooks (`provides_triage()` returns a *skill* to load; a domain verb returns a *command* to run).

**Lifecycle**: Discovered uniformly through `discover_all_extensions()` and the `skill_domains.{key}.workflow_skill_extensions` map (keyed by verb type), and resolved null-on-absent by a `manage-config resolve-*` verb — the same discovery + resolution path `provides_triage()` / `provides_outline_skill()` use. A domain returning `None` contributes no verb — the silent-skip default.

```python
def provides_domain_verb(self) -> dict | None:
    """Return this domain's executable-verb descriptor, or None.

    Returns:
        A descriptor dict ``{'verb': str, 'notation': str}`` naming the verb
        type and the resolvable script notation the domain owns, or None when
        the domain provides no such verb.

    Default: None
    """
```

**Contract only (this plan)**: The full four-face contract (declaration, discovery, dispatch, null-on-absent resolution), the sibling-ext-point mechanism rationale (NOT an extension of `ext-point-build`, NOT a `find_implementors` domain-filter generalization), and the current-plus-candidate validation live in [`ext-point-domain-verb.md`](ext-point-domain-verb.md). This registration is documentation-only — no `extension_base.py` hook and no `manage-config resolve-domain-verb` verb are wired in this plan; the Python implementation is a follow-up gated on this contract and `ADR-010`.

---

## Extension Points

Each extension point has its own contract document with formal parameters, pre-conditions, and post-conditions:

| Extension Point | Hook Method | Contract | Implementations |
|-----------------|-------------|----------|-----------------|
| Domain Bundle Manifest | `ExtensionBase` subclass + `extension.py` | [ext-point-domain-bundle.md](ext-point-domain-bundle.md) | 10 |
| Build System | `discover_modules()` + `ExecuteConfig` factory | [ext-point-build.md](ext-point-build.md) | 4 (Maven, Gradle, npm, Python) |
| Triage | `provides_triage()` | [ext-point-triage.md](ext-point-triage.md) | 7 |
| Outline | `provides_outline_skill()` | [ext-point-outline.md](ext-point-outline.md) | 1 |
| Recipe | `provides_recipes()` | [ext-point-recipe.md](ext-point-recipe.md) | 4 |
| Provider | `*_provider.py` | [ext-point-provider.md](ext-point-provider.md) | 4 |
| Domain Verb | `provides_domain_verb()` | [ext-point-domain-verb.md](ext-point-domain-verb.md) | 0 (contract only) |

See each document for the complete contract, implementation template, and current implementations.

For all extension-related configuration paths, see [marshal-json-reference.md](marshal-json-reference.md).

---

### applies_to_module

```python
def applies_to_module(self, module_data: dict,
                      active_profiles: set[str] | None = None) -> dict:
    """Check if this domain applies to a specific module and return resolved skills.

    Called during architecture enrichment to determine which skill domains
    apply to a module and what skills they provide.

    Args:
        module_data: Module dict from the module's derived.json
            (.plan/architecture/<module>/derived.json; the canonical
            module set lives in _project.json["modules"])
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

### classify_paths

Classifies each repo-relative path into a file-role bucket owned by this extension. Extensions own the predicates that decide which paths they claim and the role each claimed path plays; the aggregator in `manage-execution-manifest._classify_paths_via_extensions` collects every extension's claims and resolves overlaps. The default implementation is a no-op — extensions that do not own any file types simply do not override this method.

**Lifecycle**: Called by `manage-execution-manifest` during `phase-4-plan` Step 8b (manifest composition). The aggregator iterates every registered extension over the plan's `references.affected_files` union and uses the resolved per-path claims to derive the plan-wide bucket value.

```python
def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
    """Classify each path into a file-role bucket owned by this extension.

    Args:
        paths: Repo-relative paths to classify. Extensions ignore paths
            their globs do not match.

    Returns:
        A four-role dict keyed by ``production`` / ``test`` /
        ``documentation`` / ``config`` with list-of-claimed-paths values.

    Default: empty four-role dict (``{'production': [], 'test': [],
    'documentation': [], 'config': []}``) — explicitly NOT
    ``NotImplementedError``.
    """
```

#### Four-Role Return Shape

| Role | Semantics |
|------|-----------|
| `production` | Source code that ships to production (e.g., `scripts/foo.py`, `src/main/java/Foo.java`). |
| `test` | Test source code (e.g., `test/foo_test.py`, `src/test/java/FooIT.java`). |
| `documentation` | Human-readable documentation (e.g., `README.md`, `standards/foo.md`, `docs/foo.adoc`). |
| `config` | Build / lint / packaging configuration (e.g., `pom.xml`, `pyproject.toml`, `package.json`). |

The return dict MUST contain all four keys; extensions that own only some roles use empty lists for the others.

#### Default No-Op Behavior

The default returns `{'production': [], 'test': [], 'documentation': [], 'config': []}`. This is interpreted by the aggregator as "this extension claims nothing" and contributes no per-path claims. The default is intentionally NOT `NotImplementedError` — opting out is the common case. Extensions that own no file types (e.g., a recipe-only bundle) MAY simply not override this method.

#### Longest-Glob-Wins Overlap Resolution (Aggregator Responsibility)

When two extensions claim the same path, the **aggregator** — NOT the extension — resolves the conflict. The resolution policy:

1. Compute a specificity score for each extension's matched glob by counting non-wildcard path-segment tokens.
2. The extension with the highest specificity score wins the path under its declared role.
3. Ties break alphabetically on the extension's domain key (`d.get('domain', {}).get('key')`).

Extensions therefore return their own claims naively (i.e., based on their own predicates) and do NOT attempt to coordinate with sibling extensions. The aggregator handles cross-extension overlap.

**Example overlap**: two build systems serving the same domain (e.g. `build-maven` and `build-gradle`, both keyed under `java`) may both claim a production source path. The aggregator resolves the overlap by longest-glob-wins specificity. Documentation paths never enter overlap resolution — they are recognized generically by `manage-execution-manifest`'s `.md` / `.adoc` / `.asciidoc` suffix rule (no build owner for docs) and split out before the build extensions run. Only `BuildExtensionBase` subclasses (`build-pyproject` / `build-maven` / `build-gradle` / `build-npm`) supply production/test/config claims.

#### Unclaimed-Path Policy (Aggregator Responsibility)

A **non-documentation** path no build extension claims is tagged `unknown` by the aggregator AND surfaces as a `[STATUS]` warning naming each unclaimed path. Documentation paths are never unclaimed — the generic suffix rule always recognizes them. The aggregator **never** silently falls back to `documentation_only` or any other bucket for unclaimed code paths. The `unknown` tag forces the plan-wide bucket value to `unknown`, which downstream guards (e.g., `phase-3-outline` File-type classifier section) treat as a hard error requiring user resolution.

#### Six-Bucket Plan-Wide Output

The aggregator collapses per-path claims into one of six plan-wide bucket values that drive downstream profile and verification-step selection:

| Bucket | Triggered by |
|--------|--------------|
| `production_only` | All claimed paths are `production` (no `test`, no `documentation`). |
| `test_only` | All claimed paths are `test`. |
| `documentation_only` | All claimed paths are `documentation`. |
| `mixed_code` | Claimed paths include both `production` AND `test` but NO `documentation`. |
| `mixed_with_docs` | Claimed paths include `production` and/or `test` AND `documentation`. |
| `unknown` | At least one path was unclaimed by every registered extension. |

The `config` role does NOT influence the plan-wide bucket — config changes ride with whatever production/test/docs surface they accompany.

#### classify_path_specificity (specificity helper)

To make the longest-glob-wins resolution implementable without requiring the aggregator to introspect each extension's internal glob list, the contract also defines a companion method:

```python
def classify_path_specificity(self, path: str, role: str) -> int:
    """Non-wildcard segment count of the matched glob.

    Returns:
        Non-negative integer. Default ``0``. Extensions that override
        ``classify_paths()`` are expected to override this too, returning
        the count of explicit (non-wildcard) path-segment tokens in the
        glob that matched ``path`` for ``role``.
    """
```

The aggregator calls this method on every extension that claimed a contested path; the highest return value wins. Ties break alphabetically on the domain key. Extensions that never participate in overlap (e.g., `pm-dev-python` claiming `scripts/*.py` for `production` — no other extension owns that pattern) may leave the default `0` return in place.

#### Worked Example

Given the input path list `['scripts/foo.py', 'test/foo_test.py', 'marketplace/bundles/foo/skills/bar/SKILL.md']` and the registered build extension `build-pyproject`:

1. The generic documentation rule runs FIRST: `marketplace/bundles/foo/skills/bar/SKILL.md` ends in `.md`, so it is tagged `documentation` directly and removed from the set the build extensions see — no build owner, no extension claim.
2. `build-pyproject` (the python `BuildExtensionBase`) claims the remaining code paths: `{'production': ['scripts/foo.py'], 'test': ['test/foo_test.py'], 'documentation': [], 'config': []}`.

Final per-path map:

| Path | Role | Source |
|------|------|--------|
| `scripts/foo.py` | `production` | `build-pyproject` |
| `test/foo_test.py` | `test` | `build-pyproject` |
| `marketplace/bundles/foo/skills/bar/SKILL.md` | `documentation` | generic suffix rule (no build owner) |

Plan-wide bucket: `mixed_with_docs` (production + test + documentation present).

---

### classify_globs (build_map routes)

Declares this extension's contribution to the `build_map` file-to-build contract as a list of explicit **`(pattern, role)` routes**. Each route pairs a concrete glob pattern with one of the four resolved file roles, declaring both WHAT the domain owns and WHERE it lives. The seed aggregator consumes the routes verbatim — no tree scan enumerates one glob per directory. The default implementation is an empty list — extensions that contribute no buildable file types simply do not override this method.

**Lifecycle**: Called by `manage-config`'s `aggregate_build_map()` during `init` / `sync-defaults` / `build-map seed`. The aggregator collects every extension's routes via `derive_globs_from_tree(project_root, extensions)` (the `script-shared` route collector), stamps each `(pattern, role)` with `classify_build_class`, and writes the result into `build.map`.

```python
def classify_globs(self) -> list[tuple[str, str]]:
    """Return this extension's explicit (pattern, role) build_map routes.

    Each tuple is ``(pattern, role)`` — a concrete glob pattern paired with one
    of the four resolved file roles. The route declares both WHAT this domain
    owns and WHERE it lives, so the build_map seed consumes the routes verbatim.
    Patterns are matched with the shared route matcher (the matcher the
    downstream ``manage-execution-manifest`` build_map consumer uses): a
    path-bearing route is matched against the whole repo-relative path via
    ``fnmatch.fnmatch``, so a single ``*`` matches across ``/`` — declare
    single-``*`` globs, NOT recursive ``**`` forms; a bare config-file basename
    route (no ``/`` — e.g. ``pyproject.toml``, ``pom.xml``, ``package.json``)
    matches the file by basename *anywhere in the tree*, so a subdirectory-only
    config file is kept in the seed and matched at build-decision time, not only
    a root-level instance. A production ``.py`` outside the obvious roots (e.g.
    ``marketplace/targets/*.py`` or every
    ``marketplace/bundles/*/skills/plan-marshall-plugin/*.py``) is covered by
    declaring a route whose pattern matches it.

    Returns:
        List of ``(pattern, role)`` tuples. ``pattern`` is an fnmatch-style glob
        (e.g. ``test/*.py``) or a bare basename for a single config file (e.g.
        ``pyproject.toml``), which matches that file at any tree depth. ``role``
        is one of the four roles — ``production`` /
        ``test`` / ``documentation`` / ``config``. Example for the python domain:
        ``[('build.py', 'production'), ('marketplace/bundles/*.py', 'production'),
        ('marketplace/targets/*.py', 'production'), ('test/*.py', 'test')]``.

    Default: ``[]`` — an extension that owns no buildable file types declares no
    routes.
    """
```

#### Why explicit routes plus a completeness validator

A route declares both the pattern and the role directly, so the seed is compact — a handful of routes per domain rather than one glob per directory. Path-bearing routes use single-`*` fnmatch globs: because `fnmatch.fnmatch` lets a single `*` span `/`, `marketplace/targets/*.py` covers `marketplace/targets/generate.py` and any file beneath `targets/`, and `marketplace/bundles/*.py` covers every nested `.py` under `marketplace/bundles/`. A bare config-file basename route (no `/` — e.g. `pom.xml`, `package.json`, `tsconfig.json`) is matched by basename anywhere in the tree, so a config file that lives only in subdirectories is kept in the seed and matched at build-decision time, not only a repo-root instance. Recursive `**` forms are NOT used.

The risk an explicit-route contract carries is the inverse of an over-broad glob: an author can forget a route, leaving a production `.py` outside the declared patterns covered by no `build_class`. That omission is caught by a separate **git-tracked completeness validator** (`validate_tree_completeness` in `script-shared`). The validator scans `git ls-files`, and reports any tracked source file (suffix `.py`) that no `production`/`test` route matches. Because the scan is git-tracked-only, untracked build output (`target/**`, `.venv/**`, `node_modules/**`) is never flagged. A forgotten production module surfaces as an uncovered path; a generated file under `target/` does not.

#### Route roles

| Role | Decides | Build action |
|------|---------|--------------|
| `production` | The route claims production source. | `classify_build_class` → `compile`. |
| `test` | The route claims test source. | `classify_build_class` → `module-tests`. |
| `config` | The route claims build/lint/packaging config. | `classify_build_class` → `verify`. |

The build_map route role is one of the three resolved roles (`production` / `test` / `config`) — documentation is **not** a build_map route role (no build owner for docs), so `BUILD_MAP_ROLES` excludes it and a `documentation` route is dropped by the deriver. The role maps straight through to a `classify_build_class` build_class with no name-to-name indirection. Only `production` and `test` routes participate in the completeness validator's coverage check.

Documentation recognition is owned generically by `manage-execution-manifest`'s change-footprint classifier (a `.md` / `.adoc` / `.asciidoc` suffix rule), NOT by a build extension. See `manage-execution-manifest/standards/decision-rules.md` § "Generic documentation recognition (no build owner)".

### classify_build_class (canonical command per entry)

Maps each `(glob, role)` the aggregator holds to its **canonical-named `build_class`** — the canonical command name the entry resolves to (`compile` / `module-tests` / `verify` / `docs-validate` / `none`). There is no indirection enum: the `build_class` value IS the canonical command, so one vocabulary spans `build_map`, `derive-verification`, `architecture resolve`, and the `per_deliverable_build` list of `default:verify:{canonical}` step IDs (same meaning ⇒ same word).

**Lifecycle**: Called by `aggregate_build_map()` once per collected `(glob, role)` route to stamp the entry's `build_class` before it is written into `build.map`.

```python
def classify_build_class(self, glob: str, role: str) -> str:
    """Return the canonical-named build_class for a (glob, role) entry.

    The returned value is the canonical command name the entry resolves to:
    ``compile`` (production), ``module-tests`` (test), ``verify`` (config),
    or ``none`` (no build). The closed set equals the canonical-command
    vocabulary — there is no name-to-name indirection map. ``docs-validate``
    remains a valid build_class value the deriver handles for marketplace
    skill ``.md`` change footprints, but it is NOT produced by the role
    default below — documentation is not a build_map route role.

    Args:
        glob: The concrete glob pattern the extension declared for this route.
        role: The resolved role — ``production`` / ``test`` / ``config``.

    Returns:
        One of ``compile`` / ``module-tests`` / ``verify`` / ``none``.

    Default: a role→command map — ``production`` → ``compile``, ``test`` →
    ``module-tests``, ``config`` → ``verify``, otherwise ``none`` (including
    the ``documentation`` role, which has no build owner).
    """
```

#### Canonical build_class values

The single source of truth for the closed set is `BUILD_CLASSES` in `script-shared`'s extension constants, shared by `ExtensionBase.classify_build_class()`, the domain extensions, and their tests.

| `build_class` | Role it attaches to | Derived verification |
|---------------|---------------------|----------------------|
| `compile` | production | `compile` for the changed module |
| `module-tests` | test | `test-compile` + `module-tests` for the changed module |
| `docs-validate` | documentation | `doctor-marketplace quality-gate` (marketplace skill `.md`) / asciidoc validate (other docs) |
| `verify` | config | `verify` (full reactor for the changed module) |
| `none` | any | No command — a changed set whose only role yields `none` derives no build |

#### Worked example (build_map routes)

The python domain returns explicit routes `[('build.py', 'production'), ('marketplace/bundles/*.py', 'production'), ('marketplace/targets/*.py', 'production'), ('test/*.py', 'test')]`. The aggregator stamps each route with `classify_build_class`, producing the seeded entries:

| Route pattern | role | build_class |
|---------------|------|-------------|
| `build.py` | `production` | `compile` |
| `marketplace/bundles/*.py` | `production` | `compile` |
| `marketplace/targets/*.py` | `production` | `compile` |
| `test/*.py` | `test` | `module-tests` |

Because `fnmatch` lets a single `*` span `/`, the `marketplace/bundles/*.py` route covers every nested `.py` under `marketplace/bundles/` — including each `marketplace/bundles/<bundle>/skills/plan-marshall-plugin/extension.py` — and `marketplace/targets/*.py` covers `marketplace/targets/generate.py` and any file beneath `targets/`. A bare config-file basename route (no `/` — e.g. `pyproject.toml`, `pom.xml`, `package.json`) matches its file by basename anywhere in the tree, so a config file living only in subdirectories is kept in the seed and matched at build-decision time, not only a repo-root instance. The `build_class` of each production route is the canonical command `compile` directly. The git-tracked completeness validator confirms no tracked `.py` is left uncovered; a production module the routes forgot surfaces as an uncovered path rather than silently classifying to no build.

---

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
                        {"skill": "plan-marshall:manage-adr", "description": "ADR creation and management"},
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

    def discover_modules(self, project_root: str) -> list:
        # Delegate to script in scripts/ directory
        from _maven_cmd_discover import discover_maven_modules
        return discover_maven_modules(project_root)
```

---

## Adding a new domain

Three steps materialise a new domain bundle on top of this contract:

1. **Create the manifest skill.** `marketplace/bundles/{bundle}/skills/plan-marshall-plugin/` with a `SKILL.md` declaring `implements: plan-marshall:extension-api/standards/ext-point-domain-bundle` and a sibling `extension.py` that subclasses `ExtensionBase` and implements `get_skill_domains()`. The scanner finds the bundle by that `implements:` frontmatter declaration, not by the directory name (see [ext-point-domain-bundle.md](ext-point-domain-bundle.md)). Start from the `Minimal Extension` example above; replace the domain key, name, and profile-skill lists with your domain's content.
2. **Add domain skills.** `marketplace/bundles/{bundle}/skills/{skill}/SKILL.md` for each piece of domain knowledge the bundle provides. At minimum a `core` profile skill set so something loads during dispatches against the new domain. Implementation, module-testing, quality, and documentation profiles are added as the bundle's coverage justifies them.
3. **Run `/marshall-steward`** in the consuming project. The wizard discovers the new bundle, calls `get_skill_domains()`, writes the registration into `marshal.json` under `skill_domains.{key}`, and prompts for any optional configuration (credentials via `ext-point-provider`, profile overrides).

Adding a single hook to an existing bundle is smaller — override the relevant method on the existing `Extension` class. The wizard picks the new declaration up on re-run. For an end-to-end "minimum looks like this" example, see [`pm-dev-frontend-cui:plan-marshall-plugin`](../../../../pm-dev-frontend-cui/skills/plan-marshall-plugin/) — `get_skill_domains` only, no other overrides.

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

| Bundle | Domain Key | Triage | Outline Skill | Recipes | Credentials | Notes |
|--------|------------|--------|---------------|---------|-------------|-------|
| pm-dev-java | java | [ext-triage-java](ext-point-triage.md) | - | - | - | Base Java bundle |
| pm-dev-java-cui | java-cui | - | - | - | - | Additive to pm-dev-java |
| pm-dev-frontend | javascript | [ext-triage-js](ext-point-triage.md) | - | - | - | |
| pm-dev-python | python | [ext-triage-python](ext-point-triage.md) | - | - | - | |
| pm-dev-oci | oci-containers | [ext-triage-oci](ext-point-triage.md) | - | - | - | |
| pm-documents | documentation | [ext-triage-docs](ext-point-triage.md) | - | [recipes](ext-point-recipe.md) | - | Uses recipe for doc verification |
| pm-requirements | requirements | [ext-triage-reqs](ext-point-triage.md) | - | - | - | |
| pm-plugin-development | plan-marshall-plugin-dev | [ext-triage-plugin](ext-point-triage.md) | [ext-outline-workflow](ext-point-outline.md) | - | - | |
| plan-marshall | build, general-dev | - | - | [1 recipe](ext-point-recipe.md) | [sonar](ext-point-provider.md) | Multi-domain |

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

### Why Seven Optional Hooks?

All seven hooks (config_defaults, provides_triage, provides_outline_skill, provides_recipes, provides_retrospective_aspects, provides_arch_gate, provides_domain_verb) follow the same extension model:

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
- [marshal-json-reference.md](marshal-json-reference.md) - Central marshal.json path reference
