# Secure Design Principles

These are the timeless design-level principles that underpin every concrete control in the sibling sub-documents. Several trace directly to Saltzer & Schroeder (1975) and are reaffirmed by [OWASP Secure Product Design](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Product_Design_Cheat_Sheet.html), the [OWASP Developer Guide security principles](https://devguide.owasp.org/en/02-foundations/03-security-principles/), the [OWASP Secure-by-Design framework](https://owasp.org/www-project-secure-by-design-framework/), and [NIST SP 800-160](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-160v1r1.pdf). Apply them at design time — design-phase flaws cost roughly 100× less to fix than production flaws (see [`threat-modeling-stride.md`](threat-modeling-stride.md)), and an insecure *design* cannot be remedied by perfect code (OWASP A04, see [`owasp-top-ten.md`](owasp-top-ten.md)).

---

## Defense in Depth

Layer multiple **independent** controls so that if one fails, others continue to protect. "Multiple layers of security controls … with redundancy so if one layer fails, the other layers will still protect" (OWASP).

**Application.** Stack controls across physical/network/application/data layers: network isolation, authentication/authorization, input validation, encryption, rate-limiting, monitoring, and alerting. Use gateways, service meshes, and message buses as enforcement points between trust zones. Combine detection, mitigation, and recovery layers — no single bypass should compromise the system.

---

## Least Privilege

Every user, service, process, and tool receives only the minimum access necessary, for the minimum duration. Saltzer & Schroeder: *default to no permissions, then add specific rights incrementally.*

**Application.** Deny-by-default policies; narrowly scope service identities and API tokens; short-lived credentials; extend the principle to CI/CD pipelines and third-party integrations; periodic access reviews; enforce at gateways / service meshes / policy-as-code; RBAC + ABAC. (Concrete authorization and secret-access detail in [`authentication-authorization.md`](authentication-authorization.md) and [`secrets-handling.md`](secrets-handling.md).)

---

## Fail Securely / Fail Closed

Default to a secure (denying) state on any error, failure, or unexpected condition. Saltzer & Schroeder "fail-safe defaults": *begin with all access denied, then explicitly grant. A wrongly-denied access is reported and fixed quickly; a wrongly-granted one often goes unnoticed.*

**Application.** Circuit breakers and bulkheads to isolate failures; explicit failover / partial-functionality strategies; standardized safe error messages (no stack traces, no internal paths); allow-lists over deny-lists; degraded modes (cached / read-only) rather than cascading failure. This is the design root of the input-validation fail-closed rule ([`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md)) and of OWASP A10:2025 "Mishandling of Exceptional Conditions" — roll back incomplete transactions entirely rather than attempting partial recovery.

---

## Secure by Default

The default configuration must be the most secure possible; a user works *deliberately* to reduce security, never to enable it.

**Application.** TLS/mTLS by default; private networking / isolated subnets as the baseline; strict security headers and secure cipher suites; hardened minimal base images; secrets in a secret manager by default ([`secrets-handling.md`](secrets-handling.md)); explicit justification required for any public exposure. This is the design principle behind OWASP A05 Security Misconfiguration ([`owasp-top-ten.md`](owasp-top-ten.md)).

---

## Separation of Duties

No single individual or component controls an entire process end-to-end; critical tasks depend on two or more independent conditions. Saltzer & Schroeder "separation of privilege."

**Application.** Separate authentication from authorization; centralize authorization via policy-as-code; RBAC/ABAC; peer code review + security approval for production; dual authorization for sensitive operations; MFA + tamper-evident logging for admin operations; a DBA cannot approve their own access changes. This underpins the CI/CD separation-of-duties control in OWASP A03:2025 Software Supply Chain Failures.

---

## Complete Mediation

Every access to every object is checked for authority on **every** occasion, without exception. NIST SP 800-160: *access to all objects must be checked for authority.* OWASP: *never cache authorization decisions; validate permissions for each subsequent access request.*

**Application.** Enforce at entry points before requests reach services; validate inputs at the boundary and reject unknown fields; centralize authorization at gateways/meshes. Complete mediation is what prevents **TOCTTOU** (time-of-check-to-time-of-use) vulnerabilities and is the design basis for the "every request" authorization rule in [`authentication-authorization.md`](authentication-authorization.md).

---

## Economy of Mechanism

Keep the design as simple and minimal as feasible — simpler code has fewer exploitation paths and is easier to verify.

**Application.** Avoid unnecessary complexity; use standard, well-understood cryptographic functions (standard TLS, never bespoke crypto); prefer established auth libraries/frameworks over hand-rolled ones; centralize shared logic to prevent duplicated, inconsistent implementations.

---

## Minimize Attack Surface

Reduce the total area exposed to attack by intentional design.

**Application.** Remove unnecessary features, services, and debug modes before deployment; close unused protocols/ports (expose only HTTPS/443); eliminate redundant connections; reuse proven, patched components; evaluate every external component before adoption and treat each new integration as a risk requiring approval. (The attack-surface lens for finding what to remove is the threat model in [`threat-modeling-stride.md`](threat-modeling-stride.md).)

---

## Cross-References

- [`threat-modeling-stride.md`](threat-modeling-stride.md) — the method for surfacing where these principles must be applied.
- [`owasp-top-ten.md`](owasp-top-ten.md) — A04 Insecure Design, A05 Security Misconfiguration, A10:2025 fail-closed.
- [`authentication-authorization.md`](authentication-authorization.md) — least privilege, complete mediation, separation of duties in access control.
- [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md) — fail-closed at the boundary.
- [`secrets-handling.md`](secrets-handling.md) — least privilege and secure-by-default applied to secrets.
- Container application of least privilege (capability dropping) and secure-by-default (minimal base images): [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md).
