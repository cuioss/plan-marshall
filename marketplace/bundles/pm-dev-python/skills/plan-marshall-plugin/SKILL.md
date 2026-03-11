---
name: plan-marshall-plugin
description: Python domain extension with skill domains, module applicability, and workflow integration
user-invocable: false
---

# Plan Marshall Plugin - Python Domain

Domain extension providing Python development skill registration to plan-marshall workflows.

## Purpose

- Domain identity and workflow extensions
- Profile-based skill organization for Python projects
- Module applicability detection based on Python build systems

## Extension API

Configuration in `extension.py` implements the Extension API contract:

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `applies_to_module()` | Check Python applicability via build systems |
| `provides_triage()` | Returns `None` (future: ext-triage-python) |

## Build Operations

Build operations (pyprojectx execution, parsing, discovery) are provided by:
- `plan-marshall:build-python` - Python build execution and module discovery

## Integration

This extension is discovered by:
- `extension-api` - Domain registration
- `skill-domains` - Domain configuration
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:build-python` - Python build operations
