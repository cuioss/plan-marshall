---
name: pm-plugin-development-plan-marshall-plugin
description: Plugin development domain manifest with module discovery for plan-marshall workflow integration
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Plan Marshall Plugin - Plugin Development Domain

Domain extension providing plugin development skill registration and module discovery to plan-marshall workflows.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Axis-C edge derivation and Axis-D path attribution are opted into by multiple inheritance (`Extension(ExtensionBase, DerivationResolverBase, PathAttributionBase)`); `derive_edges()` must stay a pure function of its arguments — no filesystem access, no subprocess — and `claim_paths()` stays stateless, declaring static ownership rather than scanning the tree
- Domain identity must match the bundle name convention (plan-marshall-plugin-dev)
- Profile-based skill organization must align with plugin.json registration
- Module discovery must detect marketplace.json to avoid conflicts with pm-dev-python

## Purpose

- Domain identity and workflow extensions (triage, outline)
- Profile-based skill organization for plugin development projects
- Module discovery for marketplace bundles
- Mutual exclusivity with `pm-dev-python:plan-marshall-plugin` via marketplace.json detection

## Module Discovery

Discovers marketplace bundles as modules for the per-module architecture
layout under `.plan/project-architecture/`. `manage-architecture` writes a
top-level `_project.json` whose `modules` index is the source of truth for
which modules exist, plus one `{module}/derived.json` per indexed module
holding this extension's discovery output. Per-module subdirectories present
on disk but absent from `_project.json["modules"]` are ignored — the index is
authoritative, not the filesystem.

Each bundle in `marketplace/bundles/` becomes one such module with:

| Aspect | Value |
|--------|-------|
| Build system | `marshall-plugin` |
| Descriptor | `.claude-plugin/plugin.json` |
| Packages | Skills, agents, commands (type-prefixed) |

### Canonical Commands

Each bundle module gets the full set of canonical Python build commands via `plan-marshall:build-pyproject:pyproject_build`:

| Command | Execution |
|---------|-----------|
| `compile` | mypy on bundle sources |
| `test-compile` | mypy on bundle tests |
| `module-tests` | pytest on bundle tests |
| `quality-gate` | ruff check on bundle |
| `verify` | Full verification (compile + quality-gate + module-tests) |
| `coverage` | pytest with coverage |
| `clean` | Remove build artifacts |

### Package Types

Components are mapped to packages with type prefixes:

- `skill:{name}` - Skill directories (description from SKILL.md)
- `agent:{name}` - Agent .md files (description from frontmatter)
- `command:{name}` - Command .md files (description from frontmatter)

### Root Module

A "default" root module provides project-wide commands (no bundle filter):
- All canonical commands without bundle argument run against entire project

## Extension API

Configuration in `extension.py` implements the Extension API contract:

| Function | Axis | Purpose |
|----------|------|---------|
| `get_skill_domains()` | A | Domain metadata with profiles |
| `applies_to_module()` | A | Applicability verdict from `build_systems=marshall-plugin` or a marketplace-shaped module path |
| `discover_modules()` | A | Module discovery whose results feed each bundle's per-module `derived.json` under `.plan/project-architecture/{module}/`. Each module carries a `component_refs` list of `{target_bundle, dep_type, resolved}` entries — the bundle's outbound references, detected by the marketplace dependency engine and projected from component granularity onto bundle granularity. It ALSO runs the discovery-time language-server harvest (`scripts/lsp_harvest.py`), which appends `dep_type: lsp` references and stamps every module with an `lsp_harvest` status record. That harvest boots a language server, so it is gated on the shared machine-local `language_servers` binding and runs for no language that has none — see [`lsp-client`](../../../plan-marshall/skills/lsp-client/SKILL.md) |
| `provides_triage()` | A | Returns `pm-plugin-development:ext-triage-plugin` |
| `provides_outline_skill()` | A | Returns `pm-plugin-development:ext-outline-workflow` |
| `provides_file_globs()` | A | Declares the marketplace bundle tree (`['marketplace/bundles/**']`) seeded into `skill_domains.plan-marshall-plugin-dev.file_globs` for domain detection. A tree claim rather than a suffix claim, because what makes a file this domain's is where it lives; the Axis-D `.claude` claim is deliberately not repeated here, since that seam decides path attribution rather than skill loading. Contributes no `build.map` route |
| `provides_retrospective_aspects()` | A | Returns the `wrapper-tangle` retrospective aspect (scans plan-marshall CI-wrapper sources for tangled gh/glab + local-git mutations) |
| `derivation_resolver_id()` | C | Returns the stable provenance id `markdown`, stamped onto every edge this resolver produces |
| `derive_edges()` | C | Pure join over `component_refs` yielding `(from, to)` module pairs from the four markdown reference kinds (`script`, `skill`, `path`, `implements`). `import` entries belong to the sibling python resolver. Unresolved targets, unknown endpoints, and self-edges are suppressed and reported as aggregated `notes[]` entries — one per category with a count and a bounded sample |
| `derivation_file_patterns()` | C | Declares the file patterns this resolver derives from (`['**/*.md']`). Descriptive metadata rendered by the resolver-configuration menu, never a filter: activation is bound by resolver **id** in the machine-local `derivation_resolvers` section |
| `path_attributor_id()` | D | Returns the stable provenance id `pm-plugin-development`, stamped onto the project-local artifact claim |
| `claim_paths()` | D | Claims the whole `.claude` project-local tree for the `pm-plugin-development` module (see § Project-Local Artifact Ownership) |

## Project-Local Artifact Ownership

The plugin-development domain owns the `.claude` project-local tree through the
Axis-D path-attribution seam. The tree holds Claude Code plugin artifacts — the
project-local skills under `.claude/skills`, the slash commands under
`.claude/commands`, and the `.claude/settings.json` harness configuration — and
this domain is the one that understands that content (it owns the plugin doctor,
the marketplace inventory, and the plugin architecture standards). **Owner = who
understands the content.**

The claim is the **bare `.claude` root prefix**, so every path beneath the tree
resolves to `pm-plugin-development` uniformly — `.claude/skills/**`,
`.claude/commands/**`, `.claude/settings.json`, and any subtree added later. An
enumerated subtree list would claim only today's population and silently miss the
next one, which is the inconsistency the claim exists to end.

This is a **deliberate ownership ruling**, not a refactor side effect.
`.claude/skills` previously resolved to the `plan-marshall` module, but that was a
re-homing of a legacy inline prefix map — explicitly not a fresh ruling, with the
plugin-development question deferred. This attributor settles it, and
`plan-marshall` correspondingly keeps only `.plan` (its own runtime-state tree). A
consumer project has no `pm-plugin-development` module, so the module-existence
guard drops the claim there — exactly as it already dropped the former
`plan-marshall` claim, so no consumer-project behaviour changes.

See [`plan-marshall:extension-api` `ext-point-path-attribution.md`](../../../plan-marshall/skills/extension-api/standards/ext-point-path-attribution.md)
for the contract and [`code-intelligence.adoc`](../../../../../doc/concepts/code-intelligence.adoc)
for the substrate view.

## Integration

This extension is discovered by:
- `extension-api` - Domain registration and module discovery
- `manage-architecture` - Architecture analysis
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `pm-dev-python:plan-marshall-plugin` - Python build execution via pyproject_build.py
- `pm-plugin-development:ext-triage-plugin` - Plugin triage extension
- `pm-plugin-development:ext-outline-workflow` - Plugin outline workflow

## Canonical invocations

The canonical argparse surface for `plugin_discover.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### discover

```bash
python3 .plan/execute-script.py pm-plugin-development:plan-marshall-plugin:plugin_discover discover \
  --root ROOT
```
