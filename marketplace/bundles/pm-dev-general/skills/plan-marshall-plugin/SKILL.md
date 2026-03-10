---
name: plan-marshall-plugin
description: General development domain manifest for plan-marshall workflow integration
user-invocable: false
---

# Plan Marshall Plugin - General Development Domain

Domain manifest skill providing cross-cutting development capabilities to plan-marshall workflows.

## Purpose

Declares the general development domain configuration including:
- Domain identity (key: general-dev)
- Profile-based skill organization (code quality, documentation, testing)

## Configuration

All configuration is in `extension.py` which implements the Extension API:
- `get_skill_domains()` - Domain metadata with profiles

## Integration

This manifest is read by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
