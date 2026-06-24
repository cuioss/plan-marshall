---
name: java-security
description: "Use when reviewing or hardening Java application security — inbound input validation at trust boundaries, secure logging, secrets handling, startup configuration validation, and security anti-patterns. The focused Java security surface resolved via skills_by_profile.security."
user-invocable: false
mode: knowledge
---

# Java Application Security

**REFERENCE MODE**: This skill provides reference material for Java application security. Load specific standards on-demand based on current task. Do not load all standards at once.

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

Load progressively based on current task. **Never load all standards at once.**

### Inbound Input Validation (INBOUND surface)

```
Read: ../java-core/standards/java-input-validation.md
```

Use when validating externally-sourced inputs at the trust boundary with programmatic `jakarta.validation` (`Validator`, constraint annotations, `@Valid` cascading). Framework-agnostic; applies to any Java 21+ project.

### Security Patterns (OUTBOUND surface)

```
Read: ../java-core/standards/java-security-patterns.md
```

Use when working with authentication, encryption, secrets, or sensitive data. Covers secure-logging rules, startup configuration validation, anti-patterns (hardcoded secrets, insecure error messages, missing startup validation), and security principles.

## Surface Boundaries

The Java security surface is split across disjoint, non-overlapping homes — load the one matching the task:

| Surface | Home |
|---------|------|
| Inbound generic validation (payloads, files, CLI, queues) | `../java-core/standards/java-input-validation.md` |
| Outbound secure logging, secrets, startup validation | `../java-core/standards/java-security-patterns.md` |
| HTTP request sanitization (path/parameter/header pipelines) | `Skill: pm-dev-java-cui:cui-http` (`de.cuioss.http.security`) |
| REST-resource validation (`@Valid` on JAX-RS methods) | `Skill: pm-dev-java:java-quarkus` (`quarkus-rest-validation.md`) |
| Cross-cutting OWASP / STRIDE / secure-coding principles | `Skill: plan-marshall:persona-security-expert` |

## Related Skills

- `plan-marshall:persona-security-expert` — Cross-cutting security review identity (OWASP Top Ten, STRIDE, secure-coding principles)
- `pm-dev-java:java-core` — Core Java development standards (the standards files referenced above live under its `standards/` directory)
- `pm-dev-java:java-quarkus` — Quarkus REST input validation
- `pm-dev-java-cui:cui-http` — CUI HTTP request-sanitization security surface
