---
name: plan-marshall-plugin
description: JavaScript domain extension with skill domains, module applicability, and workflow integration
user-invocable: false
---

# Plan Marshall Plugin - JavaScript Domain

Domain extension providing JavaScript development skill registration to plan-marshall workflows.

## Purpose

- Domain identity and workflow extensions (triage)
- Profile-based skill organization for JavaScript projects
- Module applicability detection based on npm build system

## Extension API

Configuration in `extension.py` implements the Extension API contract:

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `applies_to_module()` | Check JavaScript applicability via build systems |
| `provides_triage()` | Returns `pm-dev-frontend:ext-triage-js` |

## Build Operations

Build operations (npm/npx execution, parsing, discovery) are provided by:
- `plan-marshall:build-npm` - npm build execution and module discovery

## Integration

This extension is discovered by:
- `extension-api` - Domain registration
- `skill-domains` - Domain configuration
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:build-npm` - npm build operations
