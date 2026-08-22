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

## Quality Verify Profile

This persona provides the **`quality` verify profile** for the [`ext-point-verify`](../extension-api/standards/ext-point-verify.md) findings-pipeline stage, mirroring the role `persona-security-expert` plays for the `security` profile. The adversarial-refute methodology lives in [`standards/adversarial-refute.md`](standards/adversarial-refute.md): when a producer declares `metadata.verification_profile: quality`, the orchestrator's verify pre-stage resolves that profile key to this persona and loads that standard in-context to refute each candidate quality/structural/documentation finding before triage. Confirmed findings flow on to `ext-triage-*` unchanged; refuted false positives close `rejected` and never reach triage. The stage placement and `rejected` semantics are owned by the `ext-point-verify` contract — see that document.

## Related

- [`standards/adversarial-refute.md`](standards/adversarial-refute.md) — The `quality` verify-profile methodology this persona provides, implementing `ext-point-verify` as a verify profile (the quality counterpart to the security persona's role)
- [`extension-api:ext-point-verify.md`](../extension-api/standards/ext-point-verify.md) — The verify extension-point contract the quality profile implements
