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
- `config_defaults()` - **Not overridden.** The inherited no-op is deliberate; see § Configuration

Axis-C (`DerivationResolverBase`, opted into by multiple inheritance):
- `derivation_resolver_id()` - Returns the stable provenance id `lsp`, stamped onto every edge this resolver produces
- `derive_edges()` - Pure join over the `component_refs` field discovery materializes, selecting only `lsp` entries. Reads the harvest's `lsp_harvest` status record and reports it, so a harvest that did not run is stated rather than collapsing into a zero-edge success. Unresolved targets, unknown endpoints, and self-edges are suppressed and reported as aggregated `notes[]` entries

## Configuration

**This bundle declares no configuration keys and implements no `config_defaults`.**

The harvest runs for a language exactly when that language has an enabled
`language_servers` binding in the shared machine-local run-configuration store —
the same binding [`plan-marshall:lsp-client`](../../../plan-marshall/skills/lsp-client/SKILL.md)
reads, documented in
[`run-config-standard.md`](../../../plan-marshall/skills/manage-run-config/standards/run-config-standard.md)
and set with `run_config language-server set`.

A second key naming the same server for the same language would be the parallel
configuration surface that shared store exists to prevent. Off-by-default falls out
of the same fact: the store is git-ignored, so a fresh clone has no binding and
boots no server.

## Lifecycle

The language server runs **once at discovery time**, in
`pm-plugin-development:plan-marshall-plugin:lsp_harvest`, and its references are
persisted into `derived.json`. This resolver then joins over them on each graph
query at no additional cost.

Answering queries at a cursor position is a different lifecycle and already ships
as `plan-marshall:lsp-client`. The harvest **reuses that client's session and
transport** rather than implementing a second one; what it does not share is the
process model, because a batch pass over a whole workspace and a single-position
lookup have opposite cost profiles. See `doc/concepts/code-intelligence.adoc`.

## Scope of the harvest

The `lsp_harvest` record is materialized by `pm-plugin-development`'s module
discovery, which covers marketplace-bundle modules. Where no module carries the
record, `derive_edges()` reports that no harvest ran rather than returning a
confident zero.

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
