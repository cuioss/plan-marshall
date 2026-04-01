---
name: plan-marshall-plugin
description: Documentation domain manifest for plan-marshall workflow integration
user-invocable: false
---

# Plan Marshall Plugin - Documentation Domain

Domain extension providing documentation skill registration to plan-marshall workflows.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Domain identity must match the bundle name convention (documentation)
- Profile-based skill organization must align with plugin.json registration

## Purpose

- Domain identity and workflow extensions (triage)
- Profile-based skill organization for documentation projects
- Module applicability detection based on doc directory presence

## Extension API

Configuration in `extension.py` implements the Extension API contract:

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `provides_triage()` | Returns `pm-documents:ext-triage-docs` |
| `provides_outline_skill()` | Returns `None` (uses generic outline) |
| `provides_recipes()` | Returns `recipe-doc-verify`, `recipe-verify-architecture-diagrams` |
| `provides_verify_steps()` | Returns `[]` (verification via recipe) |

## Integration

This extension is discovered by:
- `extension-api` - Domain registration
- `skill-domains` - Domain configuration
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `pm-documents:ref-asciidoc` - AsciiDoc formatting and validation
- `pm-documents:ref-documentation` - Content quality and review
