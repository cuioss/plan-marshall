---
name: persona-implementer
description: Production-code implementation persona — the work identity for building and modifying production code
user-invocable: false
mode: knowledge
implements: persona
profiles: [implementation, quality]
composes: [plan-marshall:ref-code-quality]
---

# Persona: Implementer

**REFERENCE MODE**: This skill is a persona shell. It declares the implementer work identity and the composition it resolves to; it carries no executable workflow of its own.

The implementer is the work-activity persona for building and modifying production code. Its primary profile is `implementation`; it also applies the `quality` ref so every implementation task carries the code-quality lens.

## Composition

The persona resolver (`manage-personas resolve`) flattens this persona's composition DAG into a deduped `skills[]`:

- **Base** — `plan-marshall:persona-plan-marshall-agent` (the unconditional foundational base every persona inherits).
- **Applies (ref)** — `plan-marshall:ref-code-quality`, declared in the `composes:` frontmatter (the `quality` profile maps to this ref).
- **Profile × domain** — for each entry in `profiles:` (`implementation`, `quality`), the resolver merges the `profile × {domains}` domain skills resolved via the Extension API.

## Profiles

- `implementation` (primary) — the identity profile a task with `profile: implementation` is reverse-looked-up to.
- `quality` (secondary) — applies the code-quality ref alongside implementation work.
