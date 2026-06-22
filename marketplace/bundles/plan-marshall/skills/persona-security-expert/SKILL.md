---
name: persona-security-expert
description: Security-expert persona — the work identity for security review and hardening
user-invocable: false
mode: knowledge
implements: persona
profiles: [security]
---

# Persona: Security Expert

**REFERENCE MODE**: This skill is a persona shell. It declares the security-expert work identity and the composition it resolves to; it carries no executable workflow of its own.

The security expert is the work-activity persona for security review and hardening. Its primary profile is `security`.

> **Shell only.** This is a shell that declares the persona identity and its primary profile. The substantive security content and the `APPLICABLE_PROFILES.security` entry that wires the `security` profile into domain resolution are deliverables of a later workstream (plan 05). Until that lands, this persona resolves to its base plus whatever the Extension API exposes for the `security` profile.

## Composition

The persona resolver (`manage-personas resolve`) flattens this persona's composition DAG into a deduped `skills[]`:

- **Base** — `plan-marshall:persona-plan-marshall-agent` (the unconditional foundational base every persona inherits).
- **Profile × domain** — for the `security` profile, the resolver merges the `profile × {domains}` domain skills resolved via the Extension API (added by plan 05).

## Profiles

- `security` (primary) — the identity profile a task with `profile: security` is reverse-looked-up to.
