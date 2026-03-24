---
name: plan-marshall-plugin
description: Requirements domain manifest for plan-marshall workflow integration
user-invocable: false
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

Domain manifest skill providing requirements engineering capabilities to plan-marshall workflows.

## Purpose

Declares the requirements domain configuration including:
- Domain identity (key: requirements)
- Profile-based skill organization (core, implementation, testing, quality)

## Configuration

All configuration is in `extension.py` which implements the Extension API:
- `get_skill_domains()` - Domain metadata with profiles
- `provides_triage()` - Triage skill reference or None
- `provides_outline_skill()` - Domain-specific outline skill reference or None

## Integration

This extension is discovered by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
