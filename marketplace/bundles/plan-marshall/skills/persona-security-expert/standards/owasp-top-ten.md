# OWASP Top 10 — Web Application Security Risks

The OWASP Top 10 is the recognized baseline for the most critical web-application security risks. Map every security finding to one of these categories so the review is auditable against a shared standard. The ten categories below follow the **2021** edition (the long-stable, widely-cited list); the [2025 update](#owasp-top-10-2025-update) section at the end records what changed in the released 2025 edition.

Source of record: [OWASP Top 10:2021](https://owasp.org/Top10/) and the [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/IndexTopTen.html). Each category below cites its official page.

---

## A01:2021 — Broken Access Control

**Definition.** Access control enforces policy so users cannot act outside their intended permissions. Failures enable unauthorized information disclosure, modification, or destruction of data, or execution of functions outside a user's limits. Moved from #5 (2017) to **#1** in 2021 — it maps to 34 CWEs, the most of any category.

**Attack scenarios.**
- *Parameter tampering* — an application uses unverified user input in a query. An attacker modifies a browser parameter (e.g. `acct=notmyacct`) to read another user's account data without authorization (an IDOR / BOLA).
- *Force-browsing to privileged pages* — an attacker navigates directly to a privileged URL (e.g. `/app/admin_getappInfo`). If an unauthenticated or non-admin user can reach it, the missing function-level check is the vulnerability.

**Mitigations.**
- Deny access by default, except for explicitly public resources.
- Implement a single, centralized access-control mechanism reused throughout the application; do not scatter ad-hoc checks.
- Enforce record ownership — users may access only their own records, not arbitrary IDs.
- Validate permissions server-side on every request, regardless of source (AJAX, server-side render, direct call).
- Rate-limit API access; log authorization failures and alert on repeated patterns.
- Use short-lived JWTs and OAuth revocation; prefer ABAC/ReBAC over pure RBAC for fine-grained control.
- Include functional access-control unit and integration tests in the pipeline.

See also: [`authentication-authorization.md`](authentication-authorization.md) for the IDOR/BOLA and least-privilege detail. Cheat sheets: [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [IDOR Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html). Source: [A01:2021](https://owasp.org/Top10/2021/A01_2021-Broken_Access_Control/).

---

## A02:2021 — Cryptographic Failures

**Definition.** Previously "Sensitive Data Exposure" (A3:2017), renamed to focus on the root cause: failures in cryptographic implementation or strategy that expose sensitive data. Covers hardcoded passwords, broken/weak algorithms, and insufficient entropy in random-number generation. Moved from #3 to **#2**.

**Attack scenarios.**
- *Decryption bypass via SQL injection* — an app stores encrypted card numbers but auto-decrypts on retrieval. SQL injection returns the decrypted plaintext to the attacker's query.
- *Protocol downgrade (HTTPS → HTTP)* — an attacker on an unsecured network downgrades the connection, captures the session cookie, and hijacks the session.
- *Weak password hashing / rainbow tables* — an unsalted or fast-hash password store is cracked at scale with rainbow tables or GPU acceleration.

**Mitigations.**
- Classify sensitive data per applicable law/standard (GDPR, PCI DSS); do not store it unnecessarily — discard as soon as possible.
- Encrypt sensitive data at rest with current strong algorithms; always prefer authenticated encryption (AES-256-GCM, ChaCha20-Poly1305) over bare encryption.
- Enforce TLS with forward-secrecy ciphers and HSTS for data in transit; disable deprecated protocols (TLS 1.0/1.1, SSL) and weak ciphers.
- Store passwords with adaptive, salted functions: Argon2id, scrypt, or bcrypt (see [`authentication-authorization.md`](authentication-authorization.md)).
- Use a cryptographically secure RNG for IVs and salts.

Cheat sheets: [Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html), [Transport Layer Security](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html), [Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html). Source: [A02:2021](https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/).

---

## A03:2021 — Injection

**Definition.** An application is vulnerable to injection when user-supplied data is not validated, filtered, or sanitized; dynamic queries or non-parameterized calls run without context-aware escaping; or hostile data exploits ORM search parameters. Spans SQL, NoSQL, OS command, ORM, LDAP, and Expression-Language injection — and XSS (untrusted data injected into the DOM). Slid from #1 to **#3** as parameterized-query adoption improved; still, 94% of tested applications had some form of injection.

**Attack scenarios.**
- *Direct SQL string concatenation* — `"SELECT * FROM accounts WHERE custID='" + request.getParameter("id") + "'"`. The attacker injects `' UNION SELECT SLEEP(10);--` to dump records or run stored procedures.
- *ORM injection (Hibernate)* — even an ORM is vulnerable when queries concatenate untrusted data: `FROM accounts WHERE custID='" + request.getParameter("id") + "'`.

**Mitigations (in priority order).**
- Use a safe API with a parameterized interface or a well-used ORM — avoid the interpreter entirely.
- Use prepared statements with `?` placeholders, never string concatenation.
- Apply positive (allow-list) server-side input validation as defense-in-depth (NOT as the primary injection defense — see [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md)).
- For XSS specifically, use context-aware output encoding at the sink; the domain mechanics live in [`pm-dev-frontend:javascript-security`](../../../../pm-dev-frontend/skills/javascript-security/SKILL.md).
- Enforce least-privilege database accounts; integrate SAST/DAST/IAST into CI/CD.
- Note: SQL table/column names cannot be escaped — they require allow-list mapping.

Per-language sink mechanics: [`pm-dev-python:python-security`](../../../../pm-dev-python/skills/python-security/SKILL.md), [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md). Cheat sheets: [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html), [Query Parameterization](https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html), [OS Command Injection Defense](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html), [XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html). Source: [A03:2021](https://owasp.org/Top10/2021/A03_2021-Injection/).

---

## A04:2021 — Insecure Design

**Definition.** A new 2021 category for missing or ineffective **control design** — distinct from insecure implementation. A secure design with implementation defects can be fixed in code; an insecure design cannot be remedied by perfect code because the necessary controls were never designed in. Focuses on design flaws, missing threat modeling, and absent security requirements.

**Attack scenarios.**
- *Weak credential recovery via security questions* — security questions for account recovery (which multiple people may know) fail to authenticate identity, violating NIST guidance.
- *Business-logic abuse (cinema group booking)* — a system allows group discounts up to 15 attendees before requiring a deposit; attackers book hundreds of seats across theaters at once, causing revenue loss.
- *E-commerce scalper bots* — no anti-bot protection during limited launches lets attackers bulk-buy scarce inventory and resell at profit.

**Mitigations.**
- Establish a secure development lifecycle with AppSec review at design gates.
- Use **threat modeling** for all critical flows (authentication, access control, business logic) — see [`threat-modeling-stride.md`](threat-modeling-stride.md).
- Integrate testable security requirements into user stories; write tests that prove critical flows resist the defined threat model.
- Implement plausibility checks across tiers; segregate layers and isolate tenants by design; limit per-user/per-service resource consumption.

Cheat sheets: [Threat Modeling](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html), [Abuse Case](https://cheatsheetseries.owasp.org/cheatsheets/Abuse_Case_Cheat_Sheet.html), [Attack Surface Analysis](https://cheatsheetseries.owasp.org/cheatsheets/Attack_Surface_Analysis_Cheat_Sheet.html). See also [`secure-design-principles.md`](secure-design-principles.md). Source: [A04:2021](https://owasp.org/Top10/2021/A04_2021-Insecure_Design/).

---

## A05:2021 — Security Misconfiguration

**Definition.** The application stack lacks appropriate hardening anywhere, or cloud-service permissions are misconfigured. Moved from #6 to **#5**; affected 90% of tested applications. Covers enabled unnecessary features, unchanged default credentials, exposed stack traces, disabled security features, open cloud storage, and missing security headers.

**Attack scenarios.**
- *Default admin credentials* on a sample application left on a production server.
- *Directory listing enabled* lets attackers download and reverse-engineer compiled class files to find access-control flaws.
- *Verbose error messages* expose component versions and stack traces, giving attackers reconnaissance.
- *Open cloud storage* — a bucket retains default open-to-internet permissions, exposing stored data.

**Mitigations.**
- Implement a repeatable, automated, version-controlled hardening process; deploy minimal platforms without unnecessary features, docs, or samples.
- Establish patch management that reviews configuration regularly; remove or disable all unused features, services, pages, accounts, and privileges.
- Deploy security headers (Content-Security-Policy, X-Frame-Options, HSTS, etc.); automate configuration verification across all environments.
- Use Infrastructure-as-Code for consistent, auditable configuration (this is the **secure-by-default** principle in [`secure-design-principles.md`](secure-design-principles.md)).

Container-specific hardening lives in [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md). Cheat sheets: [Infrastructure as Code Security](https://cheatsheetseries.owasp.org/cheatsheets/Infrastructure_as_Code_Security_Cheat_Sheet.html), [Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html). Source: [A05:2021](https://owasp.org/Top10/2021/A05_2021-Security_Misconfiguration/).

---

## A06:2021 — Vulnerable and Outdated Components

**Definition.** Using libraries, frameworks, or dependencies with known flaws or no current maintenance. Third-party components run with the application's privileges, so a flaw in any one can have serious impact. Hard to test because vulnerabilities are catalogued per-component, not per-practice.

**Attack scenarios.**
- *RCE via Apache Struts 2 (CVE-2017-5638)* — enabled arbitrary code execution; contributed to the Equifax breach (147 million records).
- *Unpatched IoT/biomedical devices* remain discoverable via Shodan and vulnerable to old CVEs (e.g. Heartbleed) with no remediation path but replacement.

**Mitigations.**
- Continuously inventory all client- and server-side component versions (OWASP Dependency-Check, retire.js).
- Subscribe to security bulletins; monitor CVE/NVD/OSV for known vulnerabilities.
- Obtain components only from official sources over secure links; prefer signed packages.
- Patch promptly on a risk-based schedule rather than fixed monthly/quarterly cycles.
- Remove unused dependencies and features; generate and maintain an SBOM for all dependencies (the 2025 edition expands this into [A03:2025 Software Supply Chain Failures](#owasp-top-10-2025-update)).

Cheat sheet: [Vulnerable Dependency Management](https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html). Container supply-chain controls (SBOM, signing) live in [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md). Source: [A06:2021](https://owasp.org/Top10/2021/A06_2021-Vulnerable_and_Outdated_Components/).

---

## A07:2021 — Identification and Authentication Failures

**Definition.** Previously "Broken Authentication" (A2:2017). Covers weaknesses in confirming user identity, authentication mechanisms, and session management — improper certificate validation, authentication bypass, session fixation (22 CWEs). Moved from #2 to **#7** as MFA adoption improved.

**Attack scenarios.**
- *Credential stuffing* — without automated-threat protection, attackers test breached username/password pairs; the system becomes a password oracle.
- *Weak password policy drives reuse* — legacy complexity + forced-rotation rules push users toward weak, reused passwords.
- *Session timeout exploitation* — a user closes a browser on a public machine without logging out; the next user remains authenticated.

**Mitigations.**
- Implement MFA; eliminate default credentials; check passwords against breached-password lists.
- Follow [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) evidence-based password guidance (no composition rules, no forced rotation).
- Use identical responses for all login/registration/recovery outcomes to prevent enumeration; rate-limit or progressively delay failed logins.
- Generate high-entropy session IDs server-side post-login; exclude them from URLs; invalidate on logout and timeout; store passwords with Argon2id/bcrypt/scrypt.

Full detail (password hashing parameters, session-cookie flags, MFA hierarchy) lives in [`authentication-authorization.md`](authentication-authorization.md). Cheat sheets: [Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [Credential Stuffing Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html). Source: [A07:2021](https://owasp.org/Top10/2021/A07_2021-Identification_and_Authentication_Failures/).

---

## A08:2021 — Software and Data Integrity Failures

**Definition.** A new 2021 category covering reliance on plugins, libraries, or modules from untrusted sources/repos/CDNs without integrity verification; insecure CI/CD pipelines; and unsafe deserialization (formerly its own A8:2017). Auto-update functionality that applies updates without integrity verification is a primary concern.

**Attack scenarios.**
- *Unsigned firmware updates* on routers/IoT devices let attackers distribute malicious firmware with no remediation path.
- *SolarWinds supply-chain compromise* — attackers subverted the update mechanism, distributing malicious updates to 18,000+ organizations.
- *Insecure deserialization* — a React app passes a serialized Java object (base64 `rO0…`) between client and server; the attacker tampers it for RCE.

**Mitigations.**
- Use digital signatures to verify software and data come from the expected source.
- Use supply-chain tools (OWASP Dependency-Check, CycloneDX) to verify component integrity; generate and manage an SBOM of direct and transitive dependencies.
- Ensure CI/CD pipelines have proper segregation, configuration, and access control.
- Never deserialize untrusted data without integrity/signature verification; do not send serialized objects to untrusted clients.

Per-language deserialization sinks: [`pm-dev-python:python-security`](../../../../pm-dev-python/skills/python-security/SKILL.md) (pickle/yaml), [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md). Cheat sheet: [Deserialization](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html). Source: [A08:2021](https://owasp.org/Top10/2021/A08_2021-Software_and_Data_Integrity_Failures/).

---

## A09:2021 — Security Logging and Monitoring Failures

**Definition.** Previously "Insufficient Logging & Monitoring" (A10:2017). The application lacks adequate detection, escalation, and response for active breaches — insufficient logging of critical events, inadequate analysis, missing real-time alerting, unmonitored logs. Without it, breaches go undetected (average time-to-detect exceeds 200 days). Moved from #10 to **#9**.

**Attack scenarios.**
- *Health-plan breach undetected for seven years* — no monitoring meant attackers accessed and modified 3.5 million children's health records before discovery.
- *Airline breach of ten years of passenger data* hosted at a third party, with delayed notification due to absent monitoring.
- *GDPR fine (£20M)* — a payment-record breach went undetected because detection and response were inadequate.

**Mitigations.**
- Log all login, access-control, and server-side validation failures with sufficient user context.
- **Properly encode log data to prevent log-injection attacks** (see [`secure-logging.md`](secure-logging.md)).
- Implement append-only audit trails with integrity controls; forward logs to a centralized, secure service; set alerting thresholds for suspicious patterns.
- Adopt an incident-response framework (NIST 800-61r2); deploy log-correlation tooling (ELK, Splunk).

Full detail (sensitive-data categories, CRLF/log-forging defense, OWASP Logging Vocabulary fields) lives in [`secure-logging.md`](secure-logging.md). Cheat sheets: [Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html), [Logging Vocabulary](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Vocabulary_Cheat_Sheet.html). Source: [A09:2021](https://owasp.org/Top10/2021/A09_2021-Security_Logging_and_Monitoring_Failures/).

---

## A10:2021 — Server-Side Request Forgery (SSRF)

**Definition.** SSRF occurs whenever a web application fetches a remote resource without validating the user-supplied URL, letting an attacker make the server send requests to unintended destinations — bypassing firewalls, VPNs, and network ACLs. New to the Top 10 in 2021 from the community survey. Particularly severe in cloud architectures where metadata services sit at predictable addresses.

**Attack scenarios.**
- *Internal network reconnaissance* — mapping internal hosts/ports via timing and response analysis.
- *Cloud metadata credential theft* — fetching `http://169.254.169.254/` to extract cloud credentials, enabling full account compromise.
- *Sensitive file retrieval / internal RCE* — crafting payloads to read `/etc/passwd` or reach internal services (Redis, Elasticsearch) on localhost.

**Mitigations.**
- Validate and sanitize all user-supplied URLs server-side; maintain a positive allow-list for URL schemas (http/https only), ports, and destinations.
- Segment networks and enforce deny-by-default firewall policies for non-essential intranet traffic.
- Disable HTTP redirections (to prevent redirect-chain bypass); do not return raw server responses to clients.
- Do **not** rely on deny-lists or regex — attackers have sophisticated bypass tooling. Block access to cloud metadata endpoints from application servers.

> **Note (2025):** SSRF was consolidated into A01 Broken Access Control in the 2025 edition — see below. Cheat sheet: [SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html). Source: [A10:2021](https://owasp.org/Top10/2021/A10_2021-Server-Side_Request_Forgery_(SSRF)/).

---

## OWASP Top 10 2025 Update

The **OWASP Top 10:2025** is released and live at [owasp.org/Top10/2025/](https://owasp.org/Top10/2025/). It analyzed 589 CWEs (up from ~400) across 2.8 million applications from 13 contributing organizations, with CVSS scoring from ~175,000 CVE records. Methodology is "data-informed, but not blindly data-driven": 8 categories from contributed data, 2 from the community survey.

**The 2025 list.**

| Rank | 2025 category | Change from 2021 |
|------|---------------|------------------|
| A01 | Broken Access Control | Held #1; **SSRF (A10:2021) folded in**; now explicitly covers BOLA, BFLA, SSRF, unauthorized API access |
| A02 | Security Misconfiguration | Jumped #5 → **#2**; 100% of tested apps showed misconfiguration; continuous deployment without continuous scanning drives the rise |
| A03 | **Software Supply Chain Failures** | **NEW** — expanded from A06:2021 to the entire supply chain (dependencies, build systems, CI/CD, distribution, update mechanisms); highest average exploit/impact scores despite lowest CVE coverage |
| A04 | Cryptographic Failures | Dropped #2 → #4; new guidance to prepare for **post-quantum cryptography** (high-risk systems PQC-safe by 2030) |
| A05 | Injection | Dropped #3 → #5; better front-end tooling reduces prevalence, but API parameters remain largely untested |
| A06 | Insecure Design | Dropped #4 → #6 (natural ranking shift, no consolidation) |
| A07 | Authentication Failures | Held #7; name refined from "Identification and Authentication Failures" |
| A08 | Software or Data Integrity Failures | Held #8; minor name refinement |
| A09 | Security Logging and Alerting Failures | Held #9; "Monitoring" → "**Alerting**" to emphasize detection and response |
| A10 | **Mishandling of Exceptional Conditions** | **NEW** (community vote) — improper error handling, logical errors, failing-open |

**Two new categories.**

- **A03:2025 Software Supply Chain Failures** — breakdowns or compromises in building, distributing, or updating software (compromised third-party code, tools, dependencies, build systems, distribution infrastructure). Real-world: SolarWinds, the 2025 Bybit $1.5B theft, the 2025 npm worm harvesting credentials across 500+ package versions. Mitigations: generate and centrally manage an SBOM (direct + transitive); continuously monitor CVE/NVD/OSV; obtain components only from trusted, signed sources; use staged/canary rollouts; enforce change management and separation of duties across CI/CD; patch on risk-based timelines.
- **A10:2025 Mishandling of Exceptional Conditions** — failure to prevent, detect, and respond to unusual situations, leading to crashes, resource exhaustion, sensitive-data exposure via error messages, and corrupted transaction state. Mitigations: catch errors where they occur and recover meaningfully; **always fail closed** — roll back incomplete transactions entirely rather than partial recovery; apply rate limiting/quotas/throttling; unify error handling, logging, monitoring, alerting; never expose database errors or stack traces to end users (this connects directly to the **fail-securely** principle in [`secure-design-principles.md`](secure-design-principles.md)).

**Key takeaway for reviews.** Map findings to the 2021 categories above (the stable, fully-documented set) and additionally note where the 2025 edition reframes them — especially: SSRF is now an access-control concern, supply-chain integrity is now top-tier, and exceptional-condition handling (fail-closed, no stack-trace leakage) is now an explicit category.

Sources: [2025 Introduction](https://owasp.org/Top10/2025/0x00_2025-Introduction/), [A03:2025 Software Supply Chain Failures](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/), [A10:2025 Mishandling of Exceptional Conditions](https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/).
