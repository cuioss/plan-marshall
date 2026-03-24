---
name: plan-marshall-plugin
description: CUI Java domain manifest for plan-marshall workflow integration
user-invocable: false
---

# Plan Marshall Plugin - CUI Java Domain

Domain manifest skill providing CUI-specific Java patterns.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Domain identity must match the bundle name convention (java-cui)
- Profile-based skill organization must align with plugin.json registration

## Purpose

Declares the CUI Java domain including:
- Domain identity (java-cui)
- Skills for logging, testing, and HTTP
- Profile-based skill organization

## Configuration

All configuration is in `extension.py` which implements the Extension API:
- `get_skill_domains()` - Domain metadata with profiles

## Integration

This extension is discovered by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure --domains java-cui` - Configures the domain
- `marshall-steward` wizard - Domain selection
