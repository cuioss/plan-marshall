---
name: plan-marshall-plugin
description: Python domain manifest for plan-marshall workflow integration
user-invocable: false
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
- Domain identity must match the bundle name convention (python)
- Profile-based skill organization must align with plugin.json registration

## Purpose

Declares the Python domain configuration including:
- Domain identity (key: python)
- Profile-based skill organization (core, implementation, module_testing, quality)
- Module applicability detection based on Python build systems

## Configuration

All configuration is in `extension.py` which implements the Extension API:
- `get_skill_domains()` - Domain metadata with profiles
- `applies_to_module()` - Check Python applicability via build systems and `.py` files
- `provides_triage()` - Returns `pm-dev-python:ext-triage-python`

## Detection

This domain is applicable when:
- `python` is listed in the module's `build_systems`
- `.py` files are found in source or test paths

Build operations (pyprojectx execution, parsing, discovery) are provided by `plan-marshall:build-python`, not this bundle.

## Integration

This manifest is read by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
