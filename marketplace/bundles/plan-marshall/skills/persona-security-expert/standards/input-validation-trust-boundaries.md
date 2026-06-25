# Input Validation and Trust Boundaries

A **trust boundary** is crossed whenever data enters from outside the controlled execution environment. Input validation is the discipline of rejecting externally-sourced data that fails a boundary check rather than silently coercing it through. This document covers the trust-boundary architecture, allow-list vs deny-list, canonicalization-before-validation, syntactic vs semantic validation, and fail-closed handling. It is the cross-cutting home for these concepts; per-language sink mechanics (Python `subprocess`, JS DOM sinks, Java jakarta.validation) live in the domain skills and xref back here.

Source of record: [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html), [OWASP Proactive Controls C3](https://top10proactive.owasp.org/the-top-10/c3-validate-input-and-handle-exceptions/), [OWASP Developer Guide](https://devguide.owasp.org/en/04-design/02-web-app-checklist/05-validate-inputs/).

---

## Where the Trust Boundary Is

The boundary is crossed whenever data enters from outside the controlled environment — **not just public web inputs**, but also:

- Backend feeds and message queues.
- Extranet, supplier, partner, vendor, and regulator integrations.
- API consumers (including internal services you do not control).
- Files, uploads, and external configuration.

Validate **all** data from untrusted sources, and validate **as early as possible** after it crosses the boundary. The threat-modeling discipline for *finding* every boundary is in [`threat-modeling-stride.md`](threat-modeling-stride.md); this document is what to do *at* each boundary once found.

---

## Allow-List Is the Mandatory Primary Defense

Validate input against **known-good** rules — permitted character sets, ranges, lengths, and formats. An allow-list defines what is acceptable and rejects everything else.

**Deny-list is secondary and unreliable.** It enumerates known-bad patterns and is routinely bypassed via encoding, case variation, or alternative representations. Never rely on a deny-list as the primary control. For internationalized input, use Unicode character *categories* rather than ASCII ranges so legitimate i18n input is not rejected.

---

## Canonicalization MUST Precede Validation

Convert input to its canonical/normalized form (Unicode **NFKC** or **NFKD**) *before* applying validation. Validating first leaves the door open to encoding-based obfuscation: an attacker submits an alternate encoding that passes the check, then the system canonicalizes it into the dangerous form.

For **password** normalization specifically, the applicable NIST form differs by revision: SP 800-63B (the -3 revision) specified the compatibility forms **NFKC** or **NFKD**, whereas the newer SP 800-63-4 specifies the canonical form **NFC** (or NFKC) — preferring NFC so normalization does not alter the visual content of the password. Apply NFC for password normalization under current NIST guidance; reserve the compatibility forms (NFKC/NFKD) for general canonicalize-before-validate of non-secret input.

The canonicalize-then-validate order applies to every representation: percent-encoding, Unicode normalization forms, path normalization (`../` traversal — see the per-language path-traversal mechanics in [`pm-dev-python:python-security`](../../../../pm-dev-python/skills/python-security/SKILL.md)), and case folding.

---

## Server-Side Enforcement Is Mandatory

Client-side validation is **UX only** — it is trivially bypassed (an attacker calls the API directly). Every check that matters is enforced server-side. Moreover: **log inputs that pass client checks but fail server checks** — they are a strong signal of an active attack (the legitimate client would not send them).

---

## Syntactic AND Semantic Validation

Both are required:

- **Syntactic** — correct format/structure: an SSN, date, or currency value matches its expected pattern.
- **Semantic** — correctness in the business context: start date before end date, price within an allowed range, the account referenced belongs to the calling user.

Syntactic validation alone passes a well-formed-but-wrong value (a valid-format account number the caller does not own — an [IDOR/BOLA](authentication-authorization.md), an access-control failure not solvable by format checks).

---

## Validation Is NOT the Primary Defense Against Injection

This is the most-misunderstood point and OWASP calls it out explicitly. Input validation is a **complementary, defense-in-depth** control — it is **not** the primary defense against injection. The primary defenses are sink-specific:

- **SQL injection** → parameterized queries / prepared statements.
- **XSS** → context-aware output encoding at the sink.
- **OS command injection** → argument-vector APIs, never a shell string.

Over-relying on validation-as-injection-defense is an anti-pattern. Validate at the boundary for data quality and depth-of-defense, but secure the sink with the sink-appropriate control. The per-language sink mechanics live in [`pm-dev-python:python-security`](../../../../pm-dev-python/skills/python-security/SKILL.md), [`pm-dev-frontend:javascript-security`](../../../../pm-dev-frontend/skills/javascript-security/SKILL.md), and [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md); the injection risk maps to [`owasp-top-ten.md`](owasp-top-ten.md) A03.

---

## Fail Closed

On a failed boundary check, **reject** — deny by default; never silently coerce, truncate, or best-effort-fix the value through. A validation failure is a terminal outcome for that request, handled with a generic, non-revealing error (no stack traces, no internal paths — see [`secure-design-principles.md`](secure-design-principles.md) "Fail Securely"). Returning a partial or degraded result built from invalid input inverts the control.

---

## Practical Reinforcements

- **Centralize validation** in a shared library/framework for consistent rules, less duplication, tractable review, and centralized failure logging.
- **Anchor regular expressions** to the full input (`^…$`) and avoid "any character" wildcards. Guard against **ReDoS** (catastrophic backtracking) — a regex DoS vector — by preferring linear-time / ReDoS-safe engines.
- **Validate HTTP header values** against an ASCII allow-list to prevent header injection (HTTP response splitting, CRLF) — the same CRLF discipline as [`secure-logging.md`](secure-logging.md).

---

## Cross-References

- [`threat-modeling-stride.md`](threat-modeling-stride.md) — finding every trust boundary; Tampering control mapping.
- [`owasp-top-ten.md`](owasp-top-ten.md) — A03 Injection, A01 Broken Access Control (semantic ownership checks).
- [`authentication-authorization.md`](authentication-authorization.md) — IDOR/BOLA, the access-control side of semantic validation.
- [`secure-design-principles.md`](secure-design-principles.md) — fail securely, complete mediation.
- [`secure-logging.md`](secure-logging.md) — sanitizing untrusted data at the log sink.
