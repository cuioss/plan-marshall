---
name: plan-marshall-plugin
description: Requirements domain manifest for plan-marshall workflow integration
implements: plan-marshall:extension-api/standards/ext-point-domain-bundle
user-invocable: false
mode: manifest
---

# Plan Marshall Plugin - Requirements Domain

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Domain identity must match the bundle name convention (requirements)
- Profile-based skill organization must align with plugin.json registration

## Purpose

Declares the requirements domain configuration including:
- Domain identity (key: requirements)
- Profile-based skill organization (core, implementation, testing, quality)

## Configuration

All configuration is in `extension.py` which implements the Extension API.

Axis-A (`ExtensionBase`):
- `get_skill_domains()` - Domain metadata with profiles
- `provides_triage()` - Returns `pm-requirements:ext-triage-reqs`
- `provides_file_globs()` - Returns `[]` — a deliberate empty declaration: requirements are prose documents in whatever format the project already uses, and this bundle claims no distinct requirements-document tree, so it owns no file type of its own. A project that does keep such a tree declares it with `set-inclusion`, whose operator value wins over the seed

## Integration

This extension is discovered by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
