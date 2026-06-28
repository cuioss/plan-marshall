# Authentication and Authorization

**Authentication** confirms *who* a caller is; **authorization** decides *what* they may do. They are distinct, and conflating them is the root of the #1 OWASP risk — a valid session (authenticated) does not imply permission to a given object (authorized). This document covers password storage, MFA, sessions (authentication) and access control, IDOR/BOLA, least privilege, and the RBAC/ABAC/ReBAC models (authorization). It is the cross-cutting home for these principles.

Source of record: OWASP Cheat Sheets ([Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [IDOR Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)), [OWASP ASVS](https://github.com/OWASP/ASVS), and [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html).

---

## Authentication

### Password Storage

- **Argon2id is the primary choice** — minimum 19 MiB memory, iterations = 2, parallelism = 1.
- Fallbacks: scrypt (N = 2^17, r = 8, p = 1); bcrypt (work factor ≥ 10, but note the 72-byte input limit); PBKDF2-HMAC-SHA-256 ≥ 600,000 iterations *only* where FIPS compliance is required.
- Use a unique CSPRNG salt (≥ 32 bits) per password. **Peppering** (a separate secret added before hashing) is valid defense-in-depth.

Password hashing is deliberately a *separate discipline* from general-purpose integrity hashing — a slow, memory-hard, salted KDF, never a fast SHA-family hash. The reasoning, and the integrity-hash side of the distinction, are in [`cryptography-key-management.md`](cryptography-key-management.md) ("Hashing Is Not One Thing"); the password-storage parameters above are the authoritative source for the slow-hash side. Memory-handling caveats (e.g. Java `String` is immutable and cannot be zeroed — use `char[]`/`byte[]`) are per-language and live in [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md); the secret-storage angle is in [`secrets-handling.md`](secrets-handling.md).

### Password Policy (NIST 800-63B + ASVS)

- **No composition rules** — NIST and ASVS 2.1.9 prohibit forced upper/lower/number/symbol mixes.
- Minimum 12 characters (ASVS 2.1.1; NIST floor is 8 — target 12+ for new systems); maximum ≥ 64 for passphrases.
- Allow all printable characters + space + Unicode; never truncate.
- **No periodic forced rotation** — rotate only on confirmed compromise.
- Check against a **breached-password blocklist** (ASVS 2.1.7, NIST) — e.g. HaveIBeenPwned. Use a strength meter (zxcvbn) for UX only.

### Multi-Factor Authentication

MFA is "by far the best defense" against brute-force, credential-stuffing, and password-spraying — Microsoft reports it prevents 99.9% of account compromises. Enforce across web, mobile, and API, and extend it to sensitive actions (password/email change, disabling an MFA factor, privilege elevation). Reauthenticate before changing enrolled factors. OTPs must be short-lived, single-use, rate-limited, and CSPRNG-generated.

Factor hierarchy (strongest first):

1. **FIDO2 / WebAuthn / Passkeys** — the gold standard; phishing-resistant via origin binding; the private key never leaves the device. [NIST SP 800-63B-4](https://pages.nist.gov/800-63-3/sp800-63b.html) integrates phishing-resistant authenticators into AAL2/AAL3.
2. Push notifications, TOTP apps, hardware tokens (U2F).
3. **SMS is restricted** (NIST SP 800-63B) — SIM-swap and SS7 risk; ASVS limits SMS/email to *secondary* verification only. Avoid SMS for high-assurance flows.

### Session Management

- Session tokens ≥ 64 bits entropy via CSPRNG; opaque and unpredictable; metadata held server-side.
- Cookies: `Secure`, `HttpOnly`, `SameSite=Strict` (or `Lax`; never `None` without `Secure`). Use the `__Host-` prefix. Avoid descriptive names (e.g. `PHPSESSID`).
- **Never store tokens in `localStorage`/`sessionStorage`** (XSS-readable). The browser-enforced header layer that complements secure cookies (CSP, HSTS, `frame-ancestors`) is catalogued in [`owasp-top-ten.md`](owasp-top-ten.md) (Security Headers and Content Security Policy).
- **Regenerate the session ID after login and any privilege/role change** — the core session-fixation defense. Invalidate server-side on logout.
- Enforce **both** idle and absolute timeouts server-side: OWASP idle 2–5 min (high-value) / 15–30 min (lower-risk), absolute 4–8 h. NIST reauth: AAL1 ≤ 30 days; AAL2 every 12 h or after 30 min idle; AAL3 every 12 h or after 15 min idle.

### Anti-Automation and Enumeration

- **Generic error messages** — identical responses for wrong password / non-existent / locked / disabled account ("Invalid user ID or password"), and for password recovery, to prevent user enumeration.
- **Account lockout + rate limiting** — NIST: ≤ 100 consecutive failed attempts per account; ASVS 2.2.1 anti-automation. Counter **per account, not per IP**, to resist distributed brute-force. Use exponential backoff, CAPTCHA, or risk-based throttling.
- **Reauthenticate before sensitive operations** (password/email change, MFA enroll/disable, privilege escalation, high-value transactions, recovery) — do not rely on the active session alone, as it may be hijacked.

---

## Authorization

### Deny by Default, Server-Side, Every Request

- **Deny by default** — access denied unless explicitly granted (ASVS 4.1.5). All access-control failures **fail closed** and are logged.
- **Authenticated ≠ authorized** — never assume a valid session implies permission to an object.
- Run **all** authorization checks on a trusted server-side layer, on **every** request (ASVS 4.1.1, CWE-602) — AJAX, API, and server-render each trigger a fresh check. Use a **global mechanism** (middleware/filter/decorator), never scattered ad-hoc checks. Client-side controls (hidden UI, disabled buttons) provide zero security.
- User-supplied attributes used in access decisions must not be user-manipulable (ASVS 4.1.2, CWE-639) — re-derive the effective role from the session; never trust a client-supplied role parameter.

### IDOR / BOLA — Object-Level Ownership

Insecure Direct Object Reference (web) / Broken Object-Level Authorization (API) is verifying object-level ownership on every access. Controls:

1. **User-scoped queries** — `currentUser.projects.find(id)`, **not** `Project.find(id)`.
2. **Avoid exposing identifiers** — derive the target from the session where possible.
3. Non-sequential references (UUIDs) are defense-in-depth **only**, never a substitute for an access-control check.
4. Verify permissions on every access.
5. **RBAC alone does not solve IDOR** — role membership says nothing about ownership of a specific record.

### Broken Access Control Is #1

Broken Access Control is OWASP A01 and appears in 94% of tested apps. Root causes: authn/authz confusion (a valid JWT is not authorization to an object), ad-hoc evolution, decentralized checks, and privilege creep. Controls: centralize via a Policy Decision Point / Policy Enforcement Point (PDP/PEP); use Policy-as-Code (OPA, OpenFGA, Zanzibar); scope every DB query to the authenticated identity.

### Least Privilege and the Access-Control Models

- **Least privilege** — minimum permissions per role, covering both horizontal (peer-user data) and vertical (higher-privilege) dimensions (ASVS 4.1.3, CWE-285). Audit periodically for privilege creep; over-permissioned service accounts mean a large blast radius. (Principle detail in [`secure-design-principles.md`](secure-design-principles.md).)
- **RBAC vs ABAC vs ReBAC:**
  - *RBAC* — role-based; simple but suffers role-explosion and is weak for multi-tenant.
  - *ABAC* — decisions on user + resource + environment attributes; best for fine-grained least privilege.
  - *ReBAC* — relationship-graph based (Google Zanzibar).
  - Modern best practice: **RBAC coarse-grained + ABAC fine-grained**. RBAC alone does not solve IDOR.

### Function-Level Access Control and Escalation

- **Missing function-level access control** — protect *all* sensitive endpoints, including admin, API, settings, export/import, and unlinked endpoints. "Security by obscurity" (merely not linking an endpoint) is no protection. Test by hitting endpoints directly with a lower-privilege account.
- Test and prevent **both** horizontal and vertical escalation; never trust client-supplied role/permission params; re-derive the effective role from the session.
- **Log all authorization failures** (identity, resource, timestamp, parseable); alert on repeated failures, cross-tenant attempts, and enumeration bursts; rate-limit resource-ID access to slow IDOR enumeration (logging detail in [`secure-logging.md`](secure-logging.md)).

---

## API Security

**Maps to:** CWE-285 · CWE-639 · CWE-799 · OWASP A01 · ASVS V4

APIs expose object identifiers and operations directly to clients, with no server-rendered UI to mask them — so **authorization dominates** API risk (three of the OWASP API Security Top 10's top five are authorization failures). The web access-control rules above apply in full; this section covers the API-specific shape they take plus the token and rate-limit controls particular to API surfaces.

### Authorization at the API Surface

- **Broken Object-Level Authorization (BOLA)** — the API equivalent of IDOR: a caller manipulates an object ID in the path or body (`/users/123/profile`) to reach another user's data. **Validate the caller's permission for *every* object accessed via a user-supplied ID** (the user-scoped-query rule above), and prefer non-sequential / indirect references. A valid token is not authorization to a specific object.
- **Broken Function-Level Authorization (BFLA)** — a regular user invokes an unprotected privileged endpoint (`/api/admin/delete-user`). Separate admin from regular functions and apply **default-deny role checks on every endpoint** (the missing-function-level-access-control rule above, applied to API routes).
- **Broken Object Property-Level Authorization (BOPLA)** — authorize at the **property** level, not just the object level: allow-list which properties each role may read and which it may write, and reject any attempt to modify a restricted field (the mass-assignment defense). Returning or accepting a whole object without per-property filtering leaks or lets a caller set fields they should never control.

### Token Validation (OAuth 2.0 / OIDC)

- **Validate the access token on every request** — verify the signature against the issuer's published keys, and check the `iss`, `aud`, and `exp` claims; reject a token whose audience is not this API. Pin the expected signing algorithm (never let the token header select it, and never accept `alg: none`) — the signature-verification discipline is in [`cryptography-key-management.md`](cryptography-key-management.md).
- Use **short-lived access tokens** with refresh-token rotation; support OAuth revocation so a compromised token can be cut off before its natural expiry (the short-lived-JWT control in [A01](owasp-top-ten.md)).
- Re-derive the caller's effective permissions server-side from the validated token's identity; never trust a client-supplied scope or role parameter.

### API Key Hygiene and Rate Limiting

- **Treat API keys as secrets** — issue them per-consumer, scope them to the minimum operations, store them in a secret manager, and rotate them (the storage and rotation operations are owned by [`secrets-handling.md`](secrets-handling.md)). An API key authenticates a *client*, not a *user*, and is not a substitute for per-request object-level authorization.
- **Unrestricted Resource Consumption** — enforce rate limiting and throttling per consumer, set quotas on resource-intensive operations, and cap calls to paid third-party services (SMS, email) so an attacker cannot drive cost or denial of service through the API. Rate limiting also slows the brute-force / enumeration attacks the anti-automation rules above defend against.

Cheat sheets: [REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html), [OAuth 2.0 Protocol](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html). See also the [OWASP API Security Top 10](https://owasp.org/API-Security/).

---

## Cross-References

- [`owasp-top-ten.md`](owasp-top-ten.md) — A01 Broken Access Control, A07 Authentication Failures, A02 Cryptographic Failures (password hashing), and the Security Headers / CSP catalogue.
- [`cryptography-key-management.md`](cryptography-key-management.md) — the password-hashing-vs-integrity-hashing distinction, CSPRNG for tokens/salts, token signature verification, and key storage.
- [`threat-modeling-stride.md`](threat-modeling-stride.md) — Spoofing (authentication) and Elevation of Privilege (authorization) control mappings.
- [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md) — semantic validation (ownership) as the access-control complement to syntactic checks.
- [`secrets-handling.md`](secrets-handling.md) — credential and key storage.
- [`secure-design-principles.md`](secure-design-principles.md) — least privilege, complete mediation, separation of duties.
