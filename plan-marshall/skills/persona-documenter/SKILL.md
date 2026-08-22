---
name: persona-documenter
description: Documentation persona — the work identity for authoring and maintaining project documentation
user-invocable: false
mode: knowledge
implements: persona
profiles: [documentation]
---

# Persona: Documenter

**REFERENCE MODE**: This skill is a persona shell. It declares the documenter work identity and the composition it resolves to; it carries no executable workflow of its own.

The documenter is the work-activity persona for authoring and maintaining project documentation — AsciiDoc, ADRs, interface specs, and narrative docs. Its primary profile is `documentation`.

## Composition

The persona resolver (`manage-personas resolve`) flattens this persona's composition DAG into a deduped `skills[]`:

- **Base** — `plan-marshall:persona-plan-marshall-agent` (the unconditional foundational base every persona inherits).
- **Profile × domain** — for the `documentation` profile, the resolver merges the `profile × {domains}` domain skills resolved via the Extension API.

## Profiles

- `documentation` (primary) — the identity profile a task with `profile: documentation` is reverse-looked-up to.
