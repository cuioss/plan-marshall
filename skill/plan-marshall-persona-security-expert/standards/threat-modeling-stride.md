# Threat Modeling with STRIDE

Threat modeling answers four questions ([Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/)): **What are we working on? What can go wrong? What will we do about it? Did we do enough?** STRIDE is the systematic technique for the second question — it enumerates the threat categories that can apply at each trust-boundary crossing so no class is overlooked.

Perform threat modeling during **design, before implementation** — design-phase flaws cost roughly 100× less to fix than production flaws. It is cross-functional (developers + product + security) and is revisited after architectural changes, new features, or deployment-model changes. It complements (does not replace) security code review by prioritizing the highest-risk components.

Sources: [OWASP Threat Modeling Process](https://owasp.org/www-community/Threat_Modeling_Process), [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html), [Microsoft STRIDE](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats).

---

## The Six STRIDE Threats

Each STRIDE threat is the **violation of one security property**. Modeling each crossing against all six guarantees every property is considered.

| Threat | Security property violated | Definition |
|--------|----------------------------|------------|
| **S**poofing | Authentication | Illegally using another identity's authentication information — impersonating a legitimate user, device, or system to bypass authentication. |
| **T**ampering | Integrity | Malicious modification of data — unauthorized changes to persistent data (e.g. in a database) or alteration of data in transit over an open network. |
| **R**epudiation | Non-repudiation / accountability | A user denies performing an action with no way to prove otherwise — an operation in a system that lacks tracing/audit. |
| **I**nformation disclosure | Confidentiality | Exposure of information to individuals not authorized to access it — reading a file or data in transit without authorization. |
| **D**enial of service | Availability | Denying service to valid users — making a server temporarily unavailable/unusable via resource exhaustion, DDoS, or lockouts. |
| **E**levation of privilege | Authorization | An unprivileged user gains privileged access sufficient to compromise or destroy the system — e.g. buffer overflow to root, JWT role manipulation. |

---

## Decomposition Procedure: Data-Flow Diagram + Trust Boundaries

STRIDE is applied to a **data-flow diagram (DFD)**. The DFD's canonical element types (OWASP):

| Element | Notation | Meaning |
|---------|----------|---------|
| External entity | square | Actors/systems outside the application boundary |
| Process | circle | Components that handle and transform data |
| Data store | two parallel lines | Databases, file systems, caches |
| Data flow | arrow | Directional data movement between elements |
| Trust / privilege boundary | red dotted line | A transition where the level of trust or privilege changes as data crosses a zone |

**Procedure.**

1. **Scope** — define exactly which component/service/system is being modeled.
2. **Entry points** — identify every network port, API endpoint, UI input, file upload, and external feed.
3. **Assets** — identify what is worth protecting: credentials, personal data, config secrets, capabilities, data stores.
4. **Trust levels** — assign a trust level to each external entity (anonymous, authenticated, admin, internal service).
5. **Level-0 DFD** — draw major components, data flows, and trust boundaries.
6. **Level-1+ DFDs** — draw detailed sub-system diagrams for complex flows.
7. **Place trust boundaries** — wherever trust levels change: internet ↔ DMZ, app tier ↔ DB tier, user input ↔ privileged process.
8. **Apply STRIDE systematically** — for each DFD element and each trust-boundary crossing, evaluate all six STRIDE categories.

The Microsoft SDL analogy: *secure your house by ensuring each door and window has a locking mechanism before adding an alarm system* — handle every crossing before adding higher-level detection.

---

## Per-Threat Control Mapping

For each threat that applies at a crossing, confirm at least one control exists. The mapping below ties each STRIDE category to its property and concrete controls.

- **Spoofing → Authentication**: MFA, certificate-based auth, mutual TLS (mTLS), credential vaults, avoid storing secrets. (Detail in [`authentication-authorization.md`](authentication-authorization.md) and [`secrets-handling.md`](secrets-handling.md).)
- **Tampering → Integrity**: cryptographic hashes (SHA-256+), digital signatures, MACs, TLS in transit, file-integrity monitoring, input validation, code signing, access controls. (Input validation detail in [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md).)
- **Repudiation → Non-repudiation**: tamper-proof audit trails with timestamps, digital signatures, immutable/append-only logging, periodic log audits. (Detail in [`secure-logging.md`](secure-logging.md).)
- **Information disclosure → Confidentiality**: encryption at rest and in transit (modern TLS), authorization-based access, DLP, data minimization, generic non-revealing error messages (no stack traces). (Cryptographic detail maps to [`owasp-top-ten.md`](owasp-top-ten.md) A04.)
- **Denial of service → Availability**: rate limiting/throttling, DDoS protection, resource quotas, auto-scaling, circuit breakers, authn/authz pre-filters, redundancy, load balancing.
- **Elevation of privilege → Authorization**: least privilege, access-control reviews, SAST/DAST in CI/CD, defense in depth, Privileged Access Management (PAM), patch management. (Detail in [`authentication-authorization.md`](authentication-authorization.md) and [`secure-design-principles.md`](secure-design-principles.md).)

---

## Response Strategy Per Identified Threat

For every threat surfaced, choose and **document** one response (the OWASP/Microsoft model):

- **Mitigate** — add a control that reduces likelihood or impact (the default).
- **Eliminate** — remove the feature or flow that creates the threat.
- **Transfer** — shift the risk to another party (e.g. a managed service, insurance).
- **Accept** — knowingly accept the residual risk; this MUST be documented and justified.

Mitigations must be **testable and measurable** against requirements. The Microsoft tool tracks each threat's status as `Not Started | Needs Investigation | Mitigated | Not Applicable`; carry an equivalent status so the model stays auditable.

The Manifesto's values guide the activity: design-flaw resolution over compliance checkboxes; dialogue over rigid process; progressive understanding over a single-point assessment; iterative enhancement over a one-time deliverable — combining a *systematic approach* (reproducibility) with *informed creativity*.

---

## Relationship to the Rest of This Persona

STRIDE is the **method**; the controls it points to are detailed in the sibling sub-documents. Use this document to enumerate *what can go wrong* at each boundary, then follow the cross-references to apply the concrete control. Container-specific threat modeling (the OWASP Docker Top 10 lens) lives in [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md), which xrefs back to this STRIDE method for the general procedure.
