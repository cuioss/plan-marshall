---
name: plan-marshall-plugin
description: CUI Java domain manifest for plan-marshall workflow integration
allowed-tools: Read
---

# Plan Marshall Plugin - CUI Java Domain

Domain manifest skill providing CUI-specific Java patterns.

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
