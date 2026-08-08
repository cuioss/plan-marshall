---
name: pm-dev-java-cui-plan-marshall-plugin
description: CUI Java domain manifest for plan-marshall workflow integration
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
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

All configuration is in `extension.py` which implements the Extension API. Every
hook this bundle overrides:

| Hook | Purpose |
|------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `applies_to_module()` | Applicability check — additive to the `java` domain, keyed on Maven/Gradle build systems plus `de.cuioss:*` dependency signals |
| `provides_recipes()` | Contributes the `cui-logging-enforce` recipe |
| `provides_domain_verb()` | Declares the `marker-detect` verb, resolving to `pm-dev-java-cui:search-markers` — the domain-owned OpenRewrite marker detector. Core resolves it null-on-absent, so a project without java-cui active runs no marker gate. See `plan-marshall:extension-api/standards/ext-point-domain-verb.md`. |
| `config_defaults()` | Seeds CUI-standard Maven profile mappings and the internal-profile skip list (write-once) |

## Integration

This extension is discovered by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure --domains java-cui` - Configures the domain
- `marshall-steward` wizard - Domain selection
