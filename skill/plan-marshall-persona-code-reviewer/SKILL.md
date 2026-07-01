---
name: plan-marshall-persona-code-reviewer
description: Code-review persona that composes other personas as evaluation lenses
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Persona: Code Reviewer

**REFERENCE MODE**: This skill is a persona shell. It declares the code-reviewer evaluator identity and the composition it resolves to; it carries no executable workflow of its own.

The code reviewer is a meta/evaluator persona — it has no work-activity profile of its own. Instead it composes other personas as evaluation lenses, reading a change through each composed persona's standards to judge correctness and intent. Because it owns no primary work-activity profile, it omits the `profiles:` field entirely.

## Composition

The persona resolver (`manage-personas resolve`) flattens this persona's composition DAG into a deduped `skills[]`:

- **Base** — `plan-marshall:persona-plan-marshall-agent` (the unconditional foundational base every persona inherits).
- **Composed personas (lenses)** — the work personas whose standards the reviewer reads through, declared in the `composes:` frontmatter (`persona-implementer`, `persona-module-tester`, `persona-integration-tester`, `persona-documenter`, `persona-security-expert`); the resolver recurses into each composed persona's refs and profiles, then dedups.

## Profiles

None. A meta/evaluator persona that composes other personas as lenses omits the `profiles:` field — it is never reverse-looked-up from a task's work-activity profile.
