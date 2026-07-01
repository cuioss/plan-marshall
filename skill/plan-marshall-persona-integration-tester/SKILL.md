---
name: plan-marshall-persona-integration-tester
description: Integration-testing persona — the work identity for cross-component and end-to-end test authoring
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Persona: Integration Tester

**REFERENCE MODE**: This skill is a persona shell. It declares the integration-tester work identity and the composition it resolves to; it carries no executable workflow of its own.

The integration tester is the work-activity persona for authoring cross-component and end-to-end tests that exercise real collaborators rather than isolated units. Its primary profile is `integration_testing`.

## Composition

The persona resolver (`manage-personas resolve`) flattens this persona's composition DAG into a deduped `skills[]`:

- **Base** — `plan-marshall:persona-plan-marshall-agent` (the unconditional foundational base every persona inherits).
- **Profile × domain** — for the `integration_testing` profile, the resolver merges the `profile × {domains}` domain skills resolved via the Extension API.

## Profiles

- `integration_testing` (primary) — the identity profile a task with `profile: integration_testing` is reverse-looked-up to.
