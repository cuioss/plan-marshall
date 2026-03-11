---
name: plan-marshall-plugin
description: Java domain extension with skill domains, module applicability, and workflow integration
user-invocable: false
---

# Plan Marshall Plugin - Java Domain

Domain extension providing Java development skill registration to plan-marshall workflows.

## Purpose

- Domain identity and workflow extensions (triage, verification)
- Profile-based skill organization for Java projects
- Module applicability detection based on Maven/Gradle build systems

## Extension API

Configuration in `extension.py` implements the Extension API contract:

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `applies_to_module()` | Check Java applicability via build systems |
| `provides_triage()` | Returns `pm-dev-java:ext-triage-java` |
| `provides_verify_steps()` | Java verification agents |
| `provides_recipes()` | Custom recipe definitions |

## Build Operations

Build operations (Maven/Gradle execution, parsing, discovery) are provided by:
- `plan-marshall:build-maven` - Maven build execution and module discovery
- `plan-marshall:build-gradle` - Gradle build execution and module discovery

## Integration

This extension is discovered by:
- `extension-api` - Domain registration
- `skill-domains` - Domain configuration
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:build-maven` - Maven build operations
- `plan-marshall:build-gradle` - Gradle build operations
