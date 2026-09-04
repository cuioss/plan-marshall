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

See [extension-contract.md](extension-contract.md) for the complete method contract (required `get_skill_domains()`, optional `config_defaults`, `discover_modules`, `provides_triage`, `provides_outline_skill`, `provides_recipes`, `provides_retrospective_aspects`, `provides_arch_gate`, `provides_domain_verb`, `provides_file_globs`) and the minimal / build-bundle examples. The Axis-B classification methods (`classify_paths`, `classify_path_specificity`, `classify_globs`, `classify_build_class`) are **not** available to a domain-bundle manifest — they belong to `BuildExtensionBase` and are contracted in [extension-contract.md § BuildExtensionBase Methods (Axis-B)](extension-contract.md#buildextensionbase-methods-axis-b).

### Declaring the domain's own file globs

Among the declarations a domain bundle may make is `provides_file_globs()` — the path globs that characterise the domain's own file types. It is **optional and defaults to the empty list**, so an existing manifest that does not override it stays a valid implementor with no edit. The returned globs seed `skill_domains.{domain}.file_globs`, which the domain detector reads on its glob inclusion leg; they are domain-detection knowledge and contribute no `build.map` route.

The accessor is declarable by a domain-bundle manifest's extension precisely because this ext-point's population is the one the seeding consumer reads: `discover_all_extensions()` locates a bundle's `extension.py` through the `implements:` declaration this document requires and instantiates the module's `Extension` class, and that is the population `convert_extension_to_domain_config` iterates when it writes the seed.

The build-system extensions are **outside this ext-point's population**: each exposes a `BuildExtension` class and is reached only by the separate, name-driven `discover_build_extensions()` collector, which the domain-config conversion never consults. The exclusion turns on that discovery criterion alone — a build extension does declare `get_skill_domains()`, but the domain it names carries empty `profiles` and exists only to key its `build_map` routes, so it is not a declarant of domain-detection globs. The file-type knowledge a build system owns is declared as Axis-B `classify_globs()` routes instead.

See [extension-contract.md § provides_file_globs](extension-contract.md#provides_file_globs) for the glob dialect, the authoring rule, and the seeding precedence.

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

⛔ **A structural check for `extension.py` exists but is unreachable, and no CLI
verb may be documented as invoking it.** `_cmd_extension.py`'s
`validate_extension` / `scan_extensions` validate the manifest's shape, but they
sit behind the unregistered, underscore-prefixed `_validate.py` and are called
from nowhere outside their own module and tests. See
[extension-contract.md § Validation](extension-contract.md#validation) for what
they cover and why no invocation is written down.

⛔ **The verb that IS wired covers a different population.** `validate-contracts`
selects implementors by directory-name prefix — `ext-triage-`, `ext-outline-`,
`recipe-`, `build-` (not `build-server`), plus `*_provider.py` scripts — so a
`plan-marshall-plugin` directory is never in scope and
`validate-contracts --skill {bundle}:plan-marshall-plugin` returns
`total_checked: 0` with `status: success`: a well-formed invocation over an empty
population, which reads as a pass while checking nothing. The `implements:`
declaration this document requires does **not** bring the manifest into that
population — the validator checks the field, it does not select on it.

⛔ **And runtime does not establish it either.** `load_extension_module()` catches
every failure, logs a WARNING, and returns `None`; `discover_all_extensions()`
then omits the bundle. An invalid `extension.py` is not rejected — it silently
stops existing, which is the same false-green shape as the empty-population call
above.

## Current Implementations

All 10 production bundles ship a domain-bundle manifest under `skills/plan-marshall-plugin/`:

| Bundle | Manifest Skill | Domain Key |
|--------|----------------|------------|
| plan-marshall | plan-marshall-plugin | general-dev |
| pm-dev-java | plan-marshall-plugin | java |
| pm-dev-java-cui | plan-marshall-plugin | java-cui |
| pm-dev-frontend | plan-marshall-plugin | javascript |
| pm-dev-frontend-cui | plan-marshall-plugin | javascript-cui |
| pm-dev-python | plan-marshall-plugin | python |
| pm-dev-oci | plan-marshall-plugin | oci-containers |
| pm-documents | plan-marshall-plugin | documentation |
| pm-plugin-development | plan-marshall-plugin | plan-marshall-plugin-dev |
| pm-requirements | plan-marshall-plugin | requirements |

**A bundle may register no skill domain.** `get_skill_domains()` is the one
required method, but returning `[]` is a valid answer for a bundle whose
contribution is not skills — a bundle whose whole substance is a derivation
resolver, say. Such a bundle still ships the manifest, because the manifest is how
the extension is *discovered*: the Axis-C collector spans the Axis-A discovery
path, so a bundle that skipped the manifest would register no resolver either.
Declaring an empty domain instead of none would be worse than either — it would
put a skill-less entry in front of every domain-selection surface and assert a
capability the bundle does not have.

Every bundle in the table above declares a domain key, so no shipped bundle takes
that shape today. The `lsp` resolver, which once justified one, is hosted on
`plan-marshall` beside that bundle's `general-dev` domain — see
[ext-point-derivation-resolver.md § Current implementations](ext-point-derivation-resolver.md#current-implementations)
for the roster and for the one-resolver-per-bundle cardinality that decides where
a resolver may live.

## Related Specifications

- [extension-contract.md](extension-contract.md) — Complete `extension.py` implementation contract (ExtensionBase, methods, validation, examples)
- [module-discovery.md](module-discovery.md) — Module discovery contract for build-bundle manifests
- [ext-point-recipe.md](ext-point-recipe.md) — Recipe extension point (same `implements:` identification model)
- [ext-point-finalize-step.md](ext-point-finalize-step.md) — Finalize-step extension point (same `implements:` identification model)
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference for domain registration
