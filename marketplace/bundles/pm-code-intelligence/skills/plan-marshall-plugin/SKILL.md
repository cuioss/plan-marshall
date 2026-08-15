---
name: plan-marshall-plugin
description: Code-intelligence domain manifest registering the lsp derivation resolver
implements: plan-marshall:extension-api/standards/ext-point-domain-bundle
user-invocable: false
mode: manifest
---

# Plan Marshall Plugin - Code Intelligence

Domain manifest skill registering the `lsp` derivation resolver, which contributes
module edges derived from language-server-resolved symbol references.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for extension registration
- Do not boot a language server inside `derive_edges()` — the harvest is a
  discovery-time engine, and the resolver is a pure join over its output
- Do not add a configuration mechanism here; the harvest is configured through the
  shared extension-defaults surface in `.plan/marshal.json`

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Axis-C edge derivation is opted into by multiple inheritance (`Extension(ExtensionBase, DerivationResolverBase)`); `derive_edges()` must stay a pure function of its arguments — no filesystem access, no subprocess
- The resolver imports nothing from the bundle that materializes its field

## Purpose

Registers the `lsp` resolver identity and its edge derivation. The bundle declares
**no skill domain**: it contributes an edge set rather than skills, and asserting a
domain with no skills would put an empty entry in front of every domain-selection
surface.

## Configuration

All configuration is in `extension.py`, which implements two axes of the Extension API.

Axis-A (`ExtensionBase`):
- `get_skill_domains()` - Returns `[]`; this bundle registers no skill domain
- `applies_to_module()` - Always non-applicable, for the same reason
- `config_defaults()` - Seeds the harvest defaults into `.plan/marshal.json` through the shared `ext_defaults_set_default` helper, which never overrides a user-set value

Axis-C (`DerivationResolverBase`, opted into by multiple inheritance):
- `derivation_resolver_id()` - Returns the stable provenance id `lsp`, stamped onto every edge this resolver produces
- `derive_edges()` - Pure join over the `component_refs` field discovery materializes, selecting only `lsp` entries. Reads the harvest's `lsp_harvest` status record and reports it, so a harvest that did not run is stated rather than collapsing into a zero-edge success. Unresolved targets, unknown endpoints, and self-edges are suppressed and reported as aggregated `notes[]` entries

## Configuration keys

Seeded by `config_defaults()` under the shared extension-defaults surface. The
harvest is **off by default** — it boots a language server and indexes the
workspace, a cost every crawl would otherwise pay whether or not the project wants
symbol-derived edges.

| Key | Default | Meaning |
|-----|---------|---------|
| `pm_code_intelligence.lsp.enabled` | `false` | Whether the discovery-time harvest runs at all |
| `pm_code_intelligence.lsp.python.server` | `pyright-langserver --stdio` | Server argv for the Python workspace |
| `pm_code_intelligence.lsp.timeout_seconds` | `300` | Whole-harvest wall-clock budget |

## Lifecycle

The language server runs **once at discovery time**, in
`pm-plugin-development:plan-marshall-plugin:lsp_harvest`, and its references are
persisted into `derived.json`. This resolver then joins over them on each graph
query at no additional cost.

The alternative — a warm server answering queries at a cursor position — is a
different lifecycle and deliberately not built. A batch harvester and an
interactive client cannot share one process model, and a component carrying both
would ship neither. See `doc/concepts/code-intelligence.adoc`.

## Detection

**Detection gates skill loading, not resolver registration.** The Axis-C resolver
is discovered unconditionally: `discover_derivation_resolvers()` iterates
`discover_all_extensions()`, which returns every extension regardless of whether it
applies to the current project. Whether the resolver produces edges depends on the
harvest configuration above, not on domain applicability. See
[`ext-point-derivation-resolver.md` § Discovery](../../../plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md#2-discovery).

## Integration

This manifest is read by:
- `skill-domains get-available` - Lists available domains (this bundle contributes none)
- `marshall-steward` wizard - Domain selection during project setup
