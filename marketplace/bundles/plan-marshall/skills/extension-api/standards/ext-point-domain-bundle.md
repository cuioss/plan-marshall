# Extension Point: Domain Bundle Plugin Manifest

> **Type**: Bundle Manifest Extension | **Hook Method**: `ExtensionBase` subclass + `extension.py` | **Implementations**: 10 | **Status**: Active

## Overview

A domain bundle plugin manifest is the per-bundle entry point that registers a bundle's domain identity, skill profiles, and optional workflow hooks with plan-marshall. Each bundle that participates in the planning lifecycle ships exactly one manifest: a `plan-marshall-plugin` skill directory containing a `SKILL.md` and a sibling `extension.py` that subclasses `ExtensionBase` and implements `get_skill_domains()`.

This extension point names that manifest archetype so manifests are identified by an `implements:` frontmatter declaration — the same identification model every other archetype already uses (build, triage, recipe, outline, self-review) — rather than by a hardcoded directory-name path heuristic. The `extension_discovery.py` scanner discovers each bundle's manifest by reading the `implements:` declaration from candidate `skills/*/SKILL.md` files and derives the sibling `extension.py` from the matched manifest's directory.

The full Python contract for the `extension.py` surface — `ExtensionBase` import, required and optional methods, validation rules, and complete examples — lives in [extension-contract.md](extension-contract.md). This document is the archetype-identification contract; `extension-contract.md` is the implementation contract.

## Implementor Requirements

### Implementor Frontmatter

All domain-bundle manifest skills must include in their `SKILL.md` frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-domain-bundle
```

**Frontmatter is the sole source of truth for manifest discovery.** The `find_extension_path()` scanner in `extension_discovery.py` reads the `implements:` key from each candidate `skills/*/SKILL.md` and selects the manifest whose declaration matches the canonical value above. There is no path heuristic: the scanner does **not** identify a manifest by the directory name `plan-marshall-plugin`, and it does **not** read the markdown body for a discovery signal. A manifest whose frontmatter omits the `implements:` declaration is not discovered.

### Directory Contents

A manifest skill directory contains:

| File / Directory | Required | Purpose |
|------------------|----------|---------|
| `SKILL.md` | Yes | Carries the `implements:` frontmatter declaration that identifies the manifest archetype. |
| `extension.py` | Yes | Implements `ExtensionBase` — the bundle's domain extension. Derived as the sibling of the matched `SKILL.md`. |
| `scripts/` | No | Module discovery logic or other domain-specific scripts. |

### Implementation Pattern

The manifest `extension.py` subclasses `ExtensionBase` and implements the single abstract method `get_skill_domains()`; optional hooks are overridden only when the bundle provides them:

```python
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Domain extension for {bundle}."""

    def get_skill_domains(self) -> list[dict]:
        return [{
            "domain": {
                "key": "my-domain",
                "name": "My Domain",
                "description": "What this domain covers",
            },
            "profiles": {
                "core": {"defaults": [], "optionals": []},
                "implementation": {"defaults": [], "optionals": []},
                "module_testing": {"defaults": [], "optionals": []},
                "quality": {"defaults": [], "optionals": []},
            },
        }]
```

See [extension-contract.md](extension-contract.md) for the complete method contract (required `get_skill_domains()`, optional `config_defaults`, `discover_modules`, `provides_triage`, `provides_outline_skill`, `provides_recipes`, `provides_retrospective_aspects`, `classify_paths`, `classify_globs`, `classify_build_class`) and the minimal / build-bundle examples.

## Hook API

A domain-bundle manifest is not a Python hook method on `ExtensionBase` — it IS the `ExtensionBase` subclass. Discovery and loading flow through `extension_discovery.py`:

```python
def find_extension_path(bundle_dir: Path) -> Path | None:
    """Resolve the bundle's extension.py by scanning candidate
    skills/*/SKILL.md files for the implements: declaration

        implements: plan-marshall:extension-api/standards/ext-point-domain-bundle

    and deriving the sibling extension.py from the matched manifest's
    directory. Returns None when no candidate SKILL.md declares the
    archetype or no sibling extension.py exists.

    Preserves both resolution branches:
      - source structure (marketplace/bundles/{bundle}/skills/...)
      - versioned cache structure (cache/.../{version}/skills/...)
    """
```

`discover_all_extensions()` calls `find_extension_path()` for every bundle directory and loads each resolved `extension.py`. The frontmatter declaration is the only discovery key.

## Resolution

Manifest discovery is an internal library operation, not a user-facing CLI verb. `discover_all_extensions()` in `extension_discovery.py` resolves every bundle's manifest through `find_extension_path()` (the frontmatter scanner) and loads each `extension.py`. Workflow components consume the discovery result through the library function; there is no standalone `extension_discovery` CLI subcommand for whole-marketplace discovery.

Per-extension `extension.py` validity is checked with the plugin-doctor extension validator:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate extension \
    --extension marketplace/bundles/{bundle}/skills/plan-marshall-plugin/extension.py
```

## Current Implementations

All 10 production bundles ship a domain-bundle manifest under `skills/plan-marshall-plugin/`:

| Bundle | Manifest Skill | Domain Key |
|--------|----------------|------------|
| plan-marshall | plan-marshall-plugin | build, general-dev |
| pm-dev-java | plan-marshall-plugin | java |
| pm-dev-java-cui | plan-marshall-plugin | java-cui |
| pm-dev-frontend | plan-marshall-plugin | javascript |
| pm-dev-frontend-cui | plan-marshall-plugin | javascript-cui |
| pm-dev-python | plan-marshall-plugin | python |
| pm-dev-oci | plan-marshall-plugin | oci-containers |
| pm-documents | plan-marshall-plugin | documentation |
| pm-plugin-development | plan-marshall-plugin | plan-marshall-plugin-dev |
| pm-requirements | plan-marshall-plugin | requirements |

## Related Specifications

- [extension-contract.md](extension-contract.md) — Complete `extension.py` implementation contract (ExtensionBase, methods, validation, examples)
- [module-discovery.md](module-discovery.md) — Module discovery contract for build-bundle manifests
- [ext-point-recipe.md](ext-point-recipe.md) — Recipe extension point (same `implements:` identification model)
- [ext-point-finalize-step.md](ext-point-finalize-step.md) — Finalize-step extension point (same `implements:` identification model)
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference for domain registration
