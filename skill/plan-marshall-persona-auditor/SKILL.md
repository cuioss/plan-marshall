---
name: plan-marshall-persona-auditor
description: Audit persona that composes other personas as evaluation lenses across a wide scope
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Persona: Auditor

**REFERENCE MODE**: This skill is a persona shell. It declares the auditor evaluator identity and the composition it resolves to; it carries no executable workflow of its own.

The auditor is a meta/evaluator persona — it has no work-activity profile of its own. It composes other personas as evaluation lenses to survey a wide scope for compliance, recurring patterns, and coverage gaps. Because it owns no primary work-activity profile, it omits the `profiles:` field entirely.

## Composition

The persona resolver (`manage-personas resolve`) flattens this persona's composition DAG into a deduped `skills[]`:

- **Base** — `plan-marshall:persona-plan-marshall-agent` (the unconditional foundational base every persona inherits).
- **Composed personas (lenses)** — the work personas whose standards the auditor reads through, declared in the `composes:` frontmatter (`persona-implementer`, `persona-module-tester`, `persona-integration-tester`, `persona-documenter`, `persona-security-expert`); the resolver recurses into each composed persona's refs and profiles, then dedups.

## Profiles

None. A meta/evaluator persona that composes other personas as lenses omits the `profiles:` field — it is never reverse-looked-up from a task's work-activity profile.
