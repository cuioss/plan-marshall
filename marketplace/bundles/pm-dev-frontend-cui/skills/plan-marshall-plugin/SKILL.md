---
name: plan-marshall-plugin
description: CUI JavaScript domain manifest for plan-marshall workflow integration
user-invocable: false
---

# Plan Marshall Plugin - CUI JavaScript Domain

Domain manifest skill providing CUI-specific JavaScript project patterns as an **additive extension** to `pm-dev-frontend`.

## Additive Design

This bundle extends `pm-dev-frontend` — it does not stand alone:

| Layer | Provided by | What it gives |
|-------|-------------|---------------|
| Base | `pm-dev-frontend` | JavaScript domain (`javascript`), triage, ESLint, JSDoc, Jest testing |
| Extension | `pm-dev-frontend-cui` | CUI domain (`javascript-cui`), Maven integration, project structure defaults |

The CUI extension adds the `javascript-cui` domain on top of the `javascript` domain. Both are active for CUI JavaScript projects. The `applies_to_module()` check requires `npm + maven` (dual build system), signalling a Maven-managed frontend — the defining characteristic of CUI JS modules.

## Profile Organization

**Core** — Always loaded regardless of task:
- `cui-javascript-project` as a **default**: project structure and Maven integration are fundamental to every CUI JS task, not optional extras.

**Implementation and module_testing** — No CUI-specific skills required beyond what the base `javascript` domain provides.

**Quality** — No CUI-specific skills at this time.

**Rationale for defaults vs optionals**: A skill belongs in defaults when skipping it would mean missing critical context for routine tasks. Project structure is always relevant in a CUI JS project; domain-specific utilities (e.g., HTTP patterns) are optionals because they only apply to a subset of tasks.

## Extension API

Configuration is in `extension.py`:

| Method | Purpose |
|--------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `applies_to_module()` | Detect CUI JS via `npm + maven` dual build system |
| `config_defaults()` | Set Maven profile defaults for CUI projects |

`config_defaults()` sets write-once Maven defaults (profile map and skip list) that match CUI Open Source project conventions. These are the same Maven lifecycle hooks CUI Java projects use since the frontend Maven plugin runs inside Maven.

## Integration

This extension is discovered by:
- `skill-domains get-available` - Lists available domains
- `skill-domains configure --domains javascript-cui` - Configures the domain
- `marshall-steward` wizard - Domain selection and config_defaults() application

## References

- `plan-marshall:extension-api` - Extension API contract
- `pm-dev-frontend:plan-marshall-plugin` - Base JavaScript domain
- `plan-marshall:build-maven` - Maven profile keys used in config_defaults
