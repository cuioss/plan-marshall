---
name: plan-marshall-plugin
description: OCI container domain manifest for plan-marshall workflow integration
implements: plan-marshall:extension-api/standards/ext-point-domain-bundle
user-invocable: false
mode: manifest
---

# Plan Marshall Plugin - OCI Container Domain

Domain manifest skill providing OCI container capabilities to plan-marshall workflows.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Domain identity must match the bundle name convention (oci-containers)
- Profile-based skill organization must align with plugin.json registration

## Purpose

Declares the OCI container domain configuration including:
- Domain identity (key: oci-containers)
- Profile-based skill organization (security)

## Configuration

All configuration is in `extension.py` which implements the Extension API.

Axis-A (`ExtensionBase`):
- `get_skill_domains()` - Domain metadata with profiles
- `applies_to_module()` - Check OCI applicability via container filenames, container directories, and container packaging metadata
- `provides_triage()` - Returns `pm-dev-oci:ext-triage-oci`
- `provides_file_globs()` - Declares the container-manifest globs (`Dockerfile`, `Containerfile`, the compose manifests, `.dockerignore` / `.containerignore`, and the hadolint / trivy descriptors) seeded into `skill_domains.oci-containers.file_globs` for domain detection. These files have no build owner under ADR-004, so the declaration contributes no `build.map` route and triggers no build gate

## Detection

This domain is applicable when Dockerfile, docker-compose.yml, or Containerfile exists in the project, indicating OCI container usage.

## Integration

This manifest is read by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure` - Applies domain configuration to marshal.json
- `marshall-steward` wizard - Domain selection during project setup
