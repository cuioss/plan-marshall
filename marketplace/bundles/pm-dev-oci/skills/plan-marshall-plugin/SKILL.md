---
name: plan-marshall-plugin
description: OCI container domain manifest for plan-marshall workflow integration
user-invocable: false
---

# Plan Marshall Plugin - OCI Container Domain

Domain manifest skill providing OCI container capabilities to plan-marshall workflows.

## Purpose

Declares the OCI container domain configuration including:
- Domain identity (key: oci-containers)
- Profile-based skill organization (security)

## Configuration

All configuration is in `extension.py` which implements the Extension API:
- `get_skill_domains()` - Domain metadata with profiles
- `provides_triage()` - Triage skill reference or None
- `provides_outline_skill()` - Domain-specific outline skill reference or None

## Detection

This domain is applicable when Dockerfile, docker-compose.yml, or Containerfile exists in the project, indicating OCI container usage.

## Integration

This manifest is read by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
