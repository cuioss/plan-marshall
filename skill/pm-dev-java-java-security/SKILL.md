---
name: pm-dev-java-java-security
description: "Use when reviewing or hardening Java application security — inbound input validation at trust boundaries, secure logging, secrets handling, startup configuration validation, and security anti-patterns. The focused Java security surface resolved via skills_by_profile.security; a thin pointer that delegates cross-cutting foundations upward to plan-marshall:persona-security-expert."
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Java Application Security

**REFERENCE MODE**: This skill provides reference material for Java application security. Load specific standards on-demand based on current task. Do not load all standards at once.

This skill is a **thin pointer**: it carries only Java-specific security *mechanics* and delegates the cross-cutting conceptual foundations (OWASP Top 10, STRIDE, secrets lifecycle, secure-logging principles, trust-boundary architecture, secure-design principles) upward to `Skill: plan-marshall:persona-security-expert`. There is no content duplication — the normative conceptual rules live in that persona's `standards/` only; this skill explains how those rules are realized in Java.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for Java security review and hardening tasks.

**Prohibited actions:**
- Do not log authentication tokens, passwords, secrets, certificate contents, PII, or session identifiers
- Do not hardcode secrets in source; resolve all secrets from external configuration
- Do not silently coerce invalid inbound data; reject on any constraint violation at the trust boundary
- Do not leak internal details (paths, credentials, stack internals) in error messages returned to callers

**Constraints:**
- Externally-sourced data (deserialized payloads, file inputs, CLI arguments, message-queue bodies) must be validated at the trust boundary before use
- Security configuration must be validated fail-fast at startup, not lazily at runtime
- Security events are logged; sensitive data is masked or omitted

## When to Use This Skill

Activate when:
- **Validating inbound data** — deserialized payloads, file inputs, CLI arguments, message-queue bodies at the trust boundary
- **Handling secrets** — externalizing secrets, avoiding hardcoded credentials, masking in logs
- **Securing logging** — deciding what is safe to log and what must be masked or omitted
- **Validating startup configuration** — fail-fast checks on security-relevant configuration
- **Reviewing for anti-patterns** — hardcoded secrets, sensitive-data logging, insecure error messages, missing startup validation

## Available Standards

Load progressively based on current task. **Never load all standards at once.** Both standards live under this skill's own `standards/` directory.

### Inbound Input Validation (INBOUND surface)

```text
Read: standards/java-input-validation.md
```

Use when validating externally-sourced inputs at the trust boundary with programmatic `jakarta.validation` (`Validator`, constraint annotations, `@Valid` cascading). Framework-agnostic; applies to any Java 21+ project.

### Security Patterns (OUTBOUND surface)

```text
Read: standards/java-security-patterns.md
```

Use when working with authentication, encryption, secrets, or sensitive data. Covers secure-logging rules, startup configuration validation, anti-patterns (hardcoded secrets, insecure error messages, missing startup validation), and security principles.

## Surface Boundaries

The Java security surface is split across disjoint, non-overlapping homes — load the one matching the task:

| Surface | Home |
|---------|------|
| Inbound generic validation (payloads, files, CLI, queues) | `standards/java-input-validation.md` (this skill) |
| Outbound secure logging, secrets, startup validation | `standards/java-security-patterns.md` (this skill) |
| HTTP request sanitization (path/parameter/header pipelines) | `Skill: pm-dev-java-cui:cui-http` (`de.cuioss.http.security`) |
| REST-resource validation (`@Valid` on JAX-RS methods) | `Skill: pm-dev-java:java-quarkus` (`quarkus-rest-validation.md`) |
| Cross-cutting OWASP / STRIDE / secrets / secure-logging / trust-boundary / authn-authz / secure-design foundations | `Skill: plan-marshall:persona-security-expert` |

## Cross-Cutting Foundations (delegated upward)

The conceptual *why* behind every rule in this skill's standards lives in the centralized `plan-marshall:persona-security-expert` sub-documents — load the matching one for the principle, then return here for the Java mechanics:

| Java mechanic (here) | Centralized foundation (there) |
|----------------------|-------------------------------|
| `jakarta.validation` at the trust boundary | [`input-validation-trust-boundaries.md`](../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) |
| Unsafe deserialization of inbound payloads (`ObjectInputFilter`/JEP-290 allow-listing is the Java mechanic) | [`input-validation-trust-boundaries.md`](../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) — Unsafe Deserialization sub-section |
| Secure-logging masking, never-log list | [`secure-logging.md`](../../../plan-marshall/skills/persona-security-expert/standards/secure-logging.md) |
| Externalizing secrets, no hardcoded credentials | [`secrets-handling.md`](../../../plan-marshall/skills/persona-security-expert/standards/secrets-handling.md) |
| Fail-fast startup validation, secure-by-default | [`secure-design-principles.md`](../../../plan-marshall/skills/persona-security-expert/standards/secure-design-principles.md) |
| Mapping a finding to a recognized risk category | [`owasp-top-ten.md`](../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md) |
| Threat-modeling a Java service | [`threat-modeling-stride.md`](../../../plan-marshall/skills/persona-security-expert/standards/threat-modeling-stride.md) |

## Related Skills

- `plan-marshall:persona-security-expert` — Cross-cutting security review identity and authoritative home for OWASP Top 10, STRIDE, secrets, secure logging, trust boundaries, authn/authz, and secure-design principles
- `pm-dev-java:java-core` — Core Java development standards
- `pm-dev-java:java-quarkus` — Quarkus REST input validation
- `pm-dev-java-cui:cui-http` — CUI HTTP request-sanitization security surface
