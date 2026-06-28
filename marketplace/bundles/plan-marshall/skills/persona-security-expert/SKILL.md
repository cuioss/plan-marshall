---
name: persona-security-expert
description: Security-expert persona — the work identity for security review and hardening, and the central authoritative home for cross-cutting security knowledge (OWASP Top 10, STRIDE, secrets, secure logging, trust boundaries, authn/authz, secure design)
user-invocable: false
mode: knowledge
implements: persona
profiles: [security]
---

# Persona: Security Expert

**REFERENCE MODE**: This skill is the security-expert work identity AND the deep authoritative index for cross-cutting security knowledge. It declares the persona composition it resolves to, and it indexes the nine `standards/` sub-documents that hold the substantive cross-cutting security content. Load a sub-document on-demand when its topic is in scope; do not load all nine at once.

The security expert is the work-activity persona for security review and hardening. Its primary profile is `security`. The `security` profile is registered in `ExtensionBase.APPLICABLE_PROFILES` (resolution-only — not auto-included in phase-4 task creation), so a domain declaring `skills_by_profile.security` resolves its focused per-domain security skill under this persona.

## Centralization Model

This persona is the single authoritative home for **action-general, domain-independent** security knowledge. The per-domain security skills (resolved via `skills_by_profile.security`) are **thin pointers**: they carry only the language- or runtime-specific mechanics for their domain and cross-reference *upward* to the sub-documents below for the conceptual foundations. There is no content duplication — each security topic has exactly one home:

- **Conceptual foundations** (what a trust boundary is, why allow-list beats deny-list, the STRIDE method, OWASP risk categories, secrets/logging/authn/authz principles, secure-design principles) → live here, in `standards/*.md`.
- **Domain mechanics** (jakarta.validation, `subprocess` argv vs `shell=True`, `innerHTML` vs `textContent`, container capability dropping) → live in each domain's focused security skill, which xrefs back here.

When reviewing or hardening any change, decompose the change against these foundations, then apply the relevant domain skill's mechanics.

### Cross-Map and Single-Authority Convention

The `standards/` sub-documents follow two conventions that future authors MUST preserve:

- **Single authority, xref everywhere else.** Each normative rule has exactly one owning document — algorithm and key-lifecycle rules live in `cryptography-key-management.md`, supply-chain controls in `dependency-supply-chain.md`, password hashing in `authentication-authorization.md`, and so on. An integration site that needs a rule it does not own **cross-references the owning document** rather than inline-copying the normative content. When two documents touch the same control, the non-owning side carries a one-line pointer, not a duplicated paragraph.
- **Inline framework cross-map.** Each major section carries a `**Maps to:** CWE-NNN · OWASP AXX · ASVS Vn` line so every guidance unit maps to the standard CWE / OWASP / ASVS identifiers (the cross-mapping convention adopted from Semgrep rule metadata and the agentskills framework-mapping pattern; see [`doc/concepts/design-influences.adoc`](../../../../../doc/concepts/design-influences.adoc)). OWASP category IDs use the current 2025 numbering (e.g. Cryptographic Failures = A04, Security Misconfiguration = A02, Software Supply Chain Failures = A03).

## Available Standards (load on-demand)

| Standard | Load when |
|----------|-----------|
| [`standards/owasp-top-ten.md`](standards/owasp-top-ten.md) | Auditing a change against the OWASP Top 10 risk baseline; mapping a finding to a recognized category (A01–A10) |
| [`standards/threat-modeling-stride.md`](standards/threat-modeling-stride.md) | Threat-modeling a feature: drawing a data-flow diagram, placing trust boundaries, enumerating STRIDE threats per crossing |
| [`standards/secrets-handling.md`](standards/secrets-handling.md) | Reviewing how secrets (API keys, DB passwords, tokens, keys) are stored, injected, rotated, and detected |
| [`standards/cryptography-key-management.md`](standards/cryptography-key-management.md) | Selecting cryptographic algorithms (symmetric/asymmetric/hashing/signatures) and managing the key lifecycle, envelope encryption, and TLS configuration |
| [`standards/secure-logging.md`](standards/secure-logging.md) | Reviewing what is logged vs masked, and defending against log injection (CRLF / log forging) |
| [`standards/input-validation-trust-boundaries.md`](standards/input-validation-trust-boundaries.md) | Reviewing validation at a trust boundary: allow-list vs deny-list, canonicalization-before-validation, fail-closed handling, plus SSRF / deserialization / file-upload classes |
| [`standards/authentication-authorization.md`](standards/authentication-authorization.md) | Reviewing authentication (passwords, MFA, sessions), authorization (access control, IDOR/BOLA, least privilege), and API security (token validation, rate limiting) |
| [`standards/secure-design-principles.md`](standards/secure-design-principles.md) | Evaluating the design itself: defense in depth, least privilege, fail securely, secure by default, complete mediation, configuration hardening |
| [`standards/dependency-supply-chain.md`](standards/dependency-supply-chain.md) | Reviewing dependency vetting, lock-file discipline, SBOM/provenance (SLSA), typosquat/confusion defense, and CI/CD pipeline hardening |

## Per-Domain Security Surfaces

Each per-domain skill is a thin pointer holding only its domain-specific mechanics; the conceptual foundation for every entry below lives in the centralized `standards/` sub-documents above.

| Domain | Focused security skill | Domain-specific mechanics it retains |
|--------|------------------------|--------------------------------------|
| Java | `Skill: pm-dev-java:java-security` | jakarta.validation at trust boundaries, secure logging in Java, startup config validation, secrets handling — see its own `standards/` |
| Java HTTP (CUI) | `Skill: pm-dev-java-cui:cui-http` | `de.cuioss.http.security` inbound request sanitization pipelines (review-only cross-links) |
| Python | `Skill: pm-dev-python:python-security` | injection sinks (subprocess/eval/pickle/SQL), path traversal with `Path.resolve`/`is_relative_to` |
| JavaScript | `Skill: pm-dev-frontend:javascript-security` | DOM XSS sinks (`innerHTML`/`outerHTML`/`insertAdjacentHTML`), DOMPurify, Trusted Types/CSP |
| OCI containers | `Skill: pm-dev-oci:oci-security` | runtime hardening, supply chain, OWASP **Docker** Top 10 (distinct from the web Application Top 10 above) |

## Composition

The persona resolver (`manage-personas resolve`) flattens this persona's composition DAG into a deduped `skills[]`:

- **Base** — `plan-marshall:persona-plan-marshall-agent` (the unconditional foundational base every persona inherits).
- **Profile × domain** — for the `security` profile, the resolver merges the `profile × {domains}` domain skills resolved via the Extension API (each domain's `skills_by_profile.security` declaration).

## Profiles

- `security` (primary) — the identity profile a task with `profile: security` is reverse-looked-up to.

## Standards Reference

| Standard | Purpose |
|----------|---------|
| owasp-top-ten.md | OWASP Top 10 per-category A01–A10 — definition, attack scenario, mitigations |
| threat-modeling-stride.md | STRIDE per-threat definitions, the DFD + trust-boundary decomposition procedure, and per-threat control mapping |
| secrets-handling.md | Externalizing secrets, secret-manager integration, rotation, dynamic secrets, hardcoded-credential detection |
| cryptography-key-management.md | Algorithm authority (symmetric AEAD, asymmetric, hashing, signatures), key lifecycle, envelope encryption, TLS configuration |
| secure-logging.md | What to log vs mask, sensitive-data categories, and log-injection (CRLF / log-forging) attack and prevention |
| input-validation-trust-boundaries.md | Trust-boundary architecture, allow-list vs deny-list, canonicalization-before-validation, fail-closed handling, SSRF / deserialization / file-upload |
| authentication-authorization.md | Password/MFA/session controls, access control, IDOR/BOLA, least privilege, RBAC/ABAC/ReBAC, API security |
| secure-design-principles.md | Defense in depth, least privilege, fail securely, secure by default, complete mediation, economy of mechanism, minimize attack surface, configuration hardening, exceptional conditions |
| dependency-supply-chain.md | Dependency vetting, lock files, SBOM, provenance (SLSA), artifact signing, typosquat/confusion defense, CI/CD hardening |
