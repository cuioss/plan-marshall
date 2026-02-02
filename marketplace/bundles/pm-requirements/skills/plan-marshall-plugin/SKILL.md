---
name: plan-marshall-plugin
description: Requirements domain manifest for plan-marshall workflow integration
user-invocable: false
allowed-tools: Read
---

# Plan Marshall Plugin - Requirements Domain

Domain manifest skill providing requirements engineering capabilities to plan-marshall workflows.

## Purpose

Declares the requirements domain configuration including:
- Domain identity (key: requirements)
- Profile-based skill organization (core, implementation, testing, quality)

## Configuration

All configuration is in `extension.py` which implements the Extension API:
- `get_skill_domains()` - Domain metadata with profiles
- `provides_triage()` - Triage skill reference or None
- `provides_change_type_agents()` - Change-type to agent mappings or None

## Integration

This extension is discovered by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
