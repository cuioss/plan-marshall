# Secure Logging

Logs are a double-edged control: indispensable for breach detection (OWASP [A09](owasp-top-ten.md)), yet a frequent leak vector and an attack surface in their own right. This document covers **what to log vs mask**, the sensitive-data categories, and **log injection** (CRLF / log forging) attacks and prevention. It is the cross-cutting home for these principles; per-framework masking mechanics (Logback `%replace`, custom converters, SLF4J parameterized logging) live in the domain skills and xref back here.

Source of record: [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html), [OWASP Logging Vocabulary](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Vocabulary_Cheat_Sheet.html), [OWASP Log Injection](https://owasp.org/www-community/attacks/Log_Injection), and [OWASP Top 10:2025 A09](https://owasp.org/Top10/2025/A09_2025-Security_Logging_and_Alerting_Failures/).

---

## Never Log: Secrets and Credentials

The following must never appear in logs without masking or exclusion (OWASP [CWE-532](https://cwe.mitre.org/data/definitions/532.html), Insertion of Sensitive Information into Log File):

- Authentication passwords.
- Session identification values (replace with a **hashed** value if session tracking is needed).
- Access tokens, encryption keys, and other primary secrets.
- Database connection strings.
- Application source code.
- Bank account and payment-card-holder data.
- Any data of higher security classification than the logging system is authorized to store.

The never-log rule is the logging-side complement of [`secrets-handling.md`](secrets-handling.md): a secret resolved from a vault must not then be leaked into a log line.

---

## Never Log (or Strictly De-identify): PII and Sensitive Personal Data

Exclude or de-identify: health/medical records (PHI); government identifiers (SSN, passport); financial data (card numbers, bank details, CVV); and personal names, phone numbers, and email addresses when identity is not required for the investigation. **Logs are data stores** subject to GDPR/HIPAA deletion requests, so PII in logs creates direct legal liability.

De-identification techniques, by purpose:

| Technique | Use when |
|-----------|----------|
| Deletion | The field is never needed — remove it entirely |
| Hashing | Cross-session correlation is needed without exposing the value |
| Pseudonymization | A stable coded reference is needed |
| Partial masking | Investigators need a hint (e.g. reveal last 4 digits only) |
| Tokenization | A context-preserving replacement is needed |
| Encryption | The field must be retained recoverable |

**Automate masking at the framework layer** — do not rely on developers to remember. Use a centralized, standardized log handler so masking applies uniformly rather than per call site, and audit periodically for new sensitive fields that slip through.

---

## Log Injection (CWE-117): Attack and Prevention

**Attack.** Log injection ([CWE-117](https://cwe.mitre.org/data/definitions/117.html), Improper Output Neutralization for Logs) occurs when untrusted input is written to a log without sanitization. Inserting `%0a` (newline) or `%0d%0a` (CRLF) makes the logging system interpret the injected content as a *new, legitimate log entry* — enabling an attacker to forge events, cover tracks, or corrupt the audit trail.

> Example: input `twenty-one%0a%0aINFO:+User+logged+out%3dbadguy` produces a forged `INFO: User logged out=badguy` line.

Secondary attacks: **log-file poisoning** (malicious code in a log that executes if the log becomes web-accessible) and **XSS via log viewers**.

**Prevention (in priority order).**

1. **Structured logging (JSON) — the primary defense.** JSON-encoded entries automatically escape CRLF and special characters, so forged entries cannot be injected. This is preferred because it avoids mangling legitimate input (names with apostrophes, URLs, Unicode).
2. **Sanitize event data as defense-in-depth.** Strip/encode the most dangerous control characters — CR (`\r`), LF (`\n`), tab (`\t`) and delimiter characters — on data from untrusted sources. Prefer **escaping (output encoding) over dropping**: dropping corrupts legitimate input like `O'Connor`; encoding preserves investigative value.
3. **Parameterized logging.** Use `logger.info("User input: {}", userInput)` (SLF4J style), never string concatenation.
4. **Avoid logging full attack payloads.** Record the detection rule ID and parameter name instead of the raw payload.
5. **Input validation.** Allow-list expected formats and reject non-conforming data (see [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md)).

The correct practice is **both**: JSON structured logging as the primary control, plus CRLF sanitization as defense-in-depth — not an either/or choice. The OWASP Logging Cheat Sheet itself expresses both positions.

---

## What to Log, With Sufficient Context

Log all login, access-control, and server-side input-validation **failures** with enough user context to identify a suspicious account. Capture *when, where, who, and what* for each event. The [OWASP Logging Vocabulary](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Vocabulary_Cheat_Sheet.html) minimum fields:

`datetime` (ISO 8601 + UTC offset), `appid`, event type, level, description, `useragent`, `source_ip`, `host_ip`, `hostname`, `protocol`, `port`, `request_uri`, `request_method`.

Log: authentication success and failure; authorization failures; privilege changes; input-validation failures; session lifecycle events (creation, invalidation, reuse attempts); every security-control enforcement point (success *and* failure); behavioral anomalies. Include an **interaction/correlation ID** in each event to link all entries from a single user action across services. Mark suspicious activity high-severity and trigger real-time responses (session invalidation, account lockdown) when an attack is identified.

Do **not** log private usernames when used as authentication credentials, or confidential business data beyond investigative need.

---

## Log Integrity, Access Control, and Availability

- **Integrity** — build in tamper detection so a modified/deleted record is detectable. Use append-only storage (append-only tables, write-once filesystems); move logs to read-only media as soon as possible; forward to a centralized, secure service so evidence survives a production compromise. (Corrupted logs are how attackers cover their tracks.) Honeytokens embedded in logs give high-fidelity, low-false-positive tamper detection.
- **Access control** — restrict log access by job function; only those needing debugging should see unmasked logs. Apply file permissions, audit all access, and encrypt logs containing PII or secrets.
- **Availability** — ensure logging cannot exhaust resources (an attacker-controlled logging rate is a DoS vector): monitor disk usage, rotate logs, set size limits, and separate log storage from application data.

---

## Forward to Centralized SIEM with Alerting

Forward all logs to a centralized SIEM (Splunk, ELK, LogRhythm) in a machine-readable format (JSON), with real-time alerts for anomalous activity and documented response playbooks. Adopt an incident-response framework (NIST 800-61r2). The 2025 OWASP rename from "Monitoring" to "**Alerting**" Failures emphasizes that collecting logs is not enough — detection and timely response are the point.

---

## Cross-References

- [`owasp-top-ten.md`](owasp-top-ten.md) — A09 Security Logging and Alerting Failures (the risk this document mitigates).
- [`secrets-handling.md`](secrets-handling.md) — the never-log-secrets rule and secret audit logging.
- [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md) — sanitizing untrusted input (the same boundary discipline applied to log sinks).
- Per-language secure-logging mechanics: [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md) (Java/SLF4J/Logback masking and parameterized logging).
