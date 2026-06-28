# Secure Design Principles

These are the timeless design-level principles that underpin every concrete control in the sibling sub-documents. Several trace directly to Saltzer & Schroeder and are reaffirmed by [OWASP Secure Product Design](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Product_Design_Cheat_Sheet.html), the [OWASP Developer Guide security principles](https://devguide.owasp.org/en/02-foundations/03-security-principles/), the [OWASP Secure-by-Design framework](https://owasp.org/www-project-secure-by-design-framework/), and [NIST SP 800-160](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-160v1r1.pdf). Apply them at design time — design-phase flaws cost roughly 100× less to fix than production flaws (see [`threat-modeling-stride.md`](threat-modeling-stride.md)), and an insecure *design* cannot be remedied by perfect code (OWASP A04, see [`owasp-top-ten.md`](owasp-top-ten.md)).

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

**Application.** Circuit breakers and bulkheads to isolate failures; explicit failover / partial-functionality strategies; standardized safe error messages (no stack traces, no internal paths); allow-lists over deny-lists; degraded modes (cached / read-only) rather than cascading failure. This is the design root of the input-validation fail-closed rule ([`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md)) and of the OWASP "Mishandling of Exceptional Conditions" category — roll back incomplete transactions entirely rather than attempting partial recovery.

---

## Secure by Default

The default configuration must be the most secure possible; a user works *deliberately* to reduce security, never to enable it.

**Application.** TLS/mTLS by default; private networking / isolated subnets as the baseline; strict security headers and secure cipher suites; hardened minimal base images; secrets in a secret manager by default ([`secrets-handling.md`](secrets-handling.md)); explicit justification required for any public exposure. This is the design principle behind OWASP A05 Security Misconfiguration ([`owasp-top-ten.md`](owasp-top-ten.md)).

---

## Separation of Duties

No single individual or component controls an entire process end-to-end; critical tasks depend on two or more independent conditions. Saltzer & Schroeder "separation of privilege."

**Application.** Separate authentication from authorization; centralize authorization via policy-as-code; RBAC/ABAC; peer code review + security approval for production; dual authorization for sensitive operations; MFA + tamper-evident logging for admin operations; a DBA cannot approve their own access changes. This is the design principle behind the CI/CD separation-of-duties control — the concrete pipeline mechanics (non-bypassable reviewed PRs, protected branches, signed commits, production-approval gates) live in [`dependency-supply-chain.md`](dependency-supply-chain.md).

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

**Application.** Remove unnecessary features, services, and debug modes before deployment; close unused protocols/ports (expose only HTTPS/443); eliminate redundant connections; reuse proven, patched components; evaluate every external component before adoption and treat each new integration as a risk requiring approval. The dependency-vetting and component-minimization mechanics behind that last point — vetting before adoption, removing unused dependencies, continuous composition analysis — are owned by [`dependency-supply-chain.md`](dependency-supply-chain.md). (The attack-surface lens for finding what to remove is the threat model in [`threat-modeling-stride.md`](threat-modeling-stride.md).)

---

## Mishandling of Exceptional Conditions

The *fail-securely* principle above states the rule; this section is its concrete design discipline, because the most common way a sound design leaks is through how it behaves when something goes wrong. An unhandled exceptional condition leaves the system in an indeterminate state, and a verbose error returned to the caller hands the attacker reconnaissance — a stack trace exposes component versions and internal paths, and a raw database error reveals query structure and becomes an injection road-map.

**Application.**

- **Fail to a safe (denying) default on every error path** — a failed authorization, a parse error, or a dependency timeout resolves to *deny*, never to *allow-through*. Design the default branch of every error switch to be the secure one.
- **Sanitize every error message that crosses the trust boundary** — the caller receives a generic message plus a correlation ID; the full detail (stack trace, internal path, SQL text) is logged server-side only. Route all errors through a **global/centralized exception handler** (`@RestControllerAdvice`, framework error pages, middleware) so no endpoint can leak an unmapped raw exception, and return a correct HTTP status (4xx/5xx) with the generic body.
- **Log the unexpected state, do not swallow it** — an exceptional condition is a detection signal. Record it (sanitized of secrets) so the anomaly is visible to monitoring; a silently-caught-and-ignored exception is both a reliability bug and a blind spot. The what-to-log and never-log rules are owned by [`secure-logging.md`](secure-logging.md).
- **Roll back partial state entirely** — a transaction that fails mid-way is rolled back, not left half-applied. Cleanup routines run in the handler so a failed operation never leaves the system in an inconsistent or insecure state. Apply rate limiting, quotas, and throttling so an attacker cannot drive the error path as a resource-exhaustion vector.

---

## Configuration Hardening

*Secure by default* (above) is the principle; configuration hardening is its operational discipline at deploy time. A misconfiguration — a default credential, a debug endpoint, a missing security header, an over-permissive cloud policy — is a design-intent that was correct but never enforced in the running system. It is consistently among the most prevalent real-world weaknesses precisely because it is an omission, not a coding error, so it survives code review.

**Application.**

- **Repeatable, automated, version-controlled hardening** — dev, QA, and production are configured identically from the same Infrastructure-as-Code definition (with only environment-specific credentials differing), so "it was hardened in prod but not staging" cannot happen. Verify configuration automatically across environments.
- **Least functionality** — remove unused features, components, sample apps, documentation, default accounts, open ports, and test frameworks before deployment (the minimize-attack-surface principle applied to configuration).
- **Disable defaults and debug** — change every default credential, disable debug modes and detailed error output in production (the exceptional-conditions discipline above), and reject any default that ships "open."
- **HTTP security headers** — set the browser-enforced defense layer (Content-Security-Policy, HSTS, `X-Content-Type-Options: nosniff`, `frame-ancestors`/`X-Frame-Options`, `Referrer-Policy`) as a hardening default. The directive-level catalogue of these headers lives in [`owasp-top-ten.md`](owasp-top-ten.md) (Security Misconfiguration); the TLS/HSTS transport angle is in [`cryptography-key-management.md`](cryptography-key-management.md).
- **Segmented architecture and short-lived credentials** — containerization, cloud security groups, and network ACLs to isolate tenants and tiers; prefer short-lived / federated credentials over embedded static secrets ([`secrets-handling.md`](secrets-handling.md)).

---

## Agents Rule of Two

An AI-agent surface should hold **at most two** of the three high-risk corners: (A) it processes untrusted or adversarial input, (B) it has access to sensitive systems or secrets, and (C) it can change state or communicate externally. An agent that holds all three is a single hijack away from an attacker reading secrets it can exfiltrate or acting on the project under injected instructions. Any surface that is structurally forced to hold all three corners MUST interpose a **deterministic, non-LLM containment boundary** that downgrades one corner — the LLM's good behaviour is never the control.

**Application.** plan-marshall's reader/orchestrator/writer isolation model is the worked example. The `execution-context-reader` agent is forced toward all three corners — it processes untrusted external bytes (A), holds unrestricted `Read` (B), and carries an outbound `WebFetch`/`WebSearch` channel (C). The split downgrades the state-change/exfiltration corner deterministically: the read-only reader emits only a *candidate struct* (no `Write`/`Edit`/`Bash`/`Skill`), and the deterministic `untrusted-ingestion:validate_struct` script — not reader prose — schema-enforces, length-clamps, and host-checks that struct before any write-capable context consumes it. The outbound corner (C) is further mediated by the plan-marshall-enforced WebFetch domain allowlist, which the validator re-checks via `workflow-permission-web`. The principle generalises: when corners cannot be removed (a capability list cannot path-scope `Read`), interpose a deterministic boundary rather than trusting the agent to behave.

---

## Cross-References

- [`threat-modeling-stride.md`](threat-modeling-stride.md) — the method for surfacing where these principles must be applied.
- [`owasp-top-ten.md`](owasp-top-ten.md) — Insecure Design, Security Misconfiguration (the security-header catalogue behind configuration hardening), and Mishandling of Exceptional Conditions (fail-closed).
- [`cryptography-key-management.md`](cryptography-key-management.md) — the TLS/HSTS transport hardening that configuration hardening enforces.
- [`authentication-authorization.md`](authentication-authorization.md) — least privilege, complete mediation, separation of duties in access control.
- [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md) — fail-closed at the boundary.
- [`secrets-handling.md`](secrets-handling.md) — least privilege and secure-by-default applied to secrets.
- [`dependency-supply-chain.md`](dependency-supply-chain.md) — the supply-chain application of separation of duties (CI/CD) and minimize-attack-surface (dependency vetting and minimization).
- Container application of least privilege (capability dropping) and secure-by-default (minimal base images): [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md).
- Agents Rule of Two — the concrete implementation: [`plan-marshall:untrusted-ingestion/threat-model.md`](../../untrusted-ingestion/standards/threat-model.md), the reader/orchestrator/writer isolation boundary and its deterministic `validate_struct` containment script.
- Agents Rule of Two — outbound-corner mediation: the reader's `WebFetch`/`WebSearch` channel is bounded by the plan-marshall-enforced WebFetch domain allowlist, re-checked at the validator via [`plan-marshall:workflow-permission-web`](../../workflow-permission-web/SKILL.md).
