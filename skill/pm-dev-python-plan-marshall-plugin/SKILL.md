---
name: pm-dev-python-plan-marshall-plugin
description: Python domain manifest for plan-marshall workflow integration
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Plan Marshall Plugin - Python Domain

Domain manifest skill providing Python development capabilities to plan-marshall workflows.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Axis-C edge derivation is opted into by multiple inheritance (`Extension(ExtensionBase, DerivationResolverBase)`); `derive_edges()` must stay a pure function of its arguments — no filesystem access, no subprocess
- Domain identity must match the bundle name convention (python)
- Profile-based skill organization must align with plugin.json registration

## Purpose

Declares the Python domain configuration including:
- Domain identity (key: python)
- Profile-based skill organization (core, implementation, module_testing, quality)
- Module applicability detection based on Python build systems

## Configuration

All configuration is in `extension.py`, which implements two axes of the Extension API.

Axis-A (`ExtensionBase`):
- `get_skill_domains()` - Domain metadata with profiles
- `applies_to_module()` - Check Python applicability via build systems and `.py` files
- `provides_triage()` - Returns `pm-dev-python:ext-triage-python`
- `provides_arch_gate()` - Returns the `import-linter` arch-gate tool binding (`pm-dev-python:arch-gate-python`)

Axis-C (`DerivationResolverBase`, opted into by multiple inheritance):
- `derivation_resolver_id()` - Returns the stable provenance id `python`, stamped onto every edge this resolver produces
- `derive_edges()` - Pure join over the `component_refs` field module discovery materializes, selecting only `import` entries. The four markdown reference kinds belong to the sibling `markdown` resolver on `pm-plugin-development`. Unresolved targets, unknown endpoints, and self-edges are suppressed and reported as aggregated `notes[]` entries — one per category with a count and a bounded sample. The method performs no file I/O and runs no subprocess, and imports nothing from the bundle that materializes the field

## Detection

This domain is applicable when:
- `python` is listed in the module's `build_systems`
- `.py` files are found in source or test paths

**Detection gates skill loading, not resolver registration.** The Axis-C resolver is discovered unconditionally: `discover_derivation_resolvers()` iterates `discover_all_extensions()`, which returns every extension regardless of whether it applies to the current project, and applies no `skill_domains` filter. The applicability rules above therefore have no bearing on whether the `python` resolver runs — a project with no active Python domain still gets its edges. See [`ext-point-derivation-resolver.md` § Discovery](../../../plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md#2-discovery).

Build operations (pyprojectx execution, parsing, discovery) are provided by `plan-marshall:build-pyproject`, not this bundle.

## Integration

This manifest is read by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
