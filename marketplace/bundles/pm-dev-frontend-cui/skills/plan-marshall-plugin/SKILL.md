---
name: plan-marshall-plugin
description: CUI JavaScript domain manifest for plan-marshall workflow integration
user-invocable: false
---

# Plan Marshall Plugin - CUI JavaScript Domain

Domain manifest skill providing CUI-specific JavaScript project patterns.

## Purpose

Declares the CUI JavaScript domain including:
- Domain identity (javascript-cui)
- Skills for Maven integration, project structure
- Profile-based skill organization

## Configuration

All configuration is in `extension.py` which implements the Extension API:
- `get_skill_domains()` - Domain metadata with profiles

## Integration

This extension is discovered by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure --domains javascript-cui` - Configures the domain
- `marshall-steward` wizard - Domain selection
