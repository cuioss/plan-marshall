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

## Specific Boundary-Crossing Attack Classes

The three classes below are each a distinct failure at a particular trust boundary — a *URL* the server fetches, a *byte stream* the server deserializes, a *file* the server stores. They share this document's discipline (canonicalize, allow-list, fail closed) but each has a sink-specific control that the generic rules above do not supply, so each gets its own treatment here.

### Server-Side Request Forgery (SSRF)

**Maps to:** CWE-918 · OWASP A01 · ASVS V2

**Threat.** An application fetches a remote resource using a URL it took from a request (an image-fetcher, a webhook callback, a document importer) without constraining the destination. The server — which sits *inside* the network perimeter — becomes a proxy the attacker steers at internal targets a remote client could never reach. The flagship abuse is cloud-credential theft: a request for `http://169.254.169.254/` reaches the instance metadata service and returns the host's IAM credentials, escalating to full account compromise. Attackers also use SSRF for internal port-scanning and to hit unauthenticated internal services (Redis, Elasticsearch) bound to localhost.

**Mitigation.** Validate the **host** of the user-supplied URL against a strict **allow-list** of trusted destinations — never accept and follow an arbitrary attacker-supplied URL. Restrict the scheme to `http`/`https`, and **disable HTTP redirect following** so an allow-listed host cannot 302-bounce the request into the internal range. Block the cloud metadata endpoint and migrate to a hardened metadata service (e.g. AWS IMDSv2 with IMDSv1 disabled). Enforce **network egress controls** — outbound firewall rules that permit only the legitimate downstream services — as the defense-in-depth layer behind the application check. Mitigate **DNS rebinding** by resolving the hostname **once**, validating that the resolved IP address does not fall into private or link-local ranges, and then making the request **directly to that IP** while passing the original hostname in the HTTP `Host` header (and verifying the TLS certificate against the hostname) — this prevents the TOCTOU race where a re-resolution at request time returns a different (private) IP than was validated. Deny-lists of private CIDR ranges (`127/8`, `10/8`, `172.16/12`, `192.168/16`, link-local) are a **last resort only** — they are bypassed via hex/octal/decimal IP encodings and DNS rebinding, so they never substitute for the host allow-list.

**Detection.** Log every outbound fetch with its resolved destination; alert on requests to private/link-local addresses or the metadata IP. A fetch whose resolved host fell outside the allow-list is a high-signal indicator of an active probe.

### Unsafe Deserialization of Untrusted Data

**Maps to:** CWE-502 · OWASP A08 · ASVS V2

**Threat.** Deserializing an attacker-controlled byte stream with a *native* object format reconstructs whatever object graph the bytes describe — which lets an attacker instantiate unexpected types and trigger "gadget chains" already on the classpath, escalating to denial of service, access-control bypass, or remote code execution. The danger is that the vulnerability lives in the *act of deserializing*, before any application code inspects the result, so input validation "after" deserialization is too late.

**Mitigation.** **Never deserialize untrusted data with a native serialization format.** Prefer pure-data interchange (JSON, XML) parsed with a restricted, type-constrained parser, and **cryptographically sign or authenticate** any serialized payload before deserializing it so a tampered stream is rejected up front. Per-language sink mechanics: Java — install an `ObjectInputFilter` allow-list (JEP-290 / `-Djdk.serialFilter`), mark sensitive fields `private transient`, and avoid `XMLDecoder` and vulnerable XStream versions; Python — avoid `pickle` entirely for untrusted input and use `yaml.safe_load()` rather than `yaml.load()` (see [`pm-dev-python:python-security`](../../../../pm-dev-python/skills/python-security/SKILL.md)); .NET — avoid `BinaryFormatter` (it cannot be secured), set `TypeNameHandling.None`, and use a `SerializationBinder` allow-list. Java sink detail lives in [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md).

**Detection.** Flag any call that deserializes a request-sourced stream with a native deserializer (`ObjectInputStream.readObject`, `pickle.load`, `BinaryFormatter.Deserialize`). A base64 blob beginning with a known native-serialization magic prefix (Java `rO0`, Python pickle opcodes) crossing the boundary is a strong tampering signal.

### Unrestricted File Upload

**Maps to:** CWE-434 · OWASP A02 · ASVS V5

**Threat.** An upload endpoint that trusts the client-declared type or filename lets an attacker store executable content in a web-accessible location and run it — `shell.jpg.php`, a double-extension or null-byte trick (`shell.php%00.jpg`), or a polyglot file that is both a valid image and a valid script. Execution of the uploaded file yields server takeover. Decompression bombs (a tiny archive expanding to gigabytes) are the denial-of-service variant.

**Mitigation.** Validate the file **type by content / magic bytes, not by the `Content-Type` header or the extension**, and rewrite images to strip embedded payloads. Apply an extension **allow-list evaluated *after* the filename is fully decoded** (defeating double-extension and `%00` tricks) — never a deny-list. Enforce **size limits measured post-decompression** plus rate limits to stop zip bombs. **Store uploads outside the web root** and serve them through an application handler that maps opaque IDs to files, with **randomized filenames** (UUIDs, no caller-supplied extension). Run malware / content-disarm-and-reconstruction scanning before the file is stored, **never permit script execution in upload directories** (web-server configuration plus least-privilege filesystem permissions), and enforce authorization before any stored file is served.

**Detection.** Reject-and-log every upload whose magic-byte type disagrees with its declared type or fails the extension allow-list; these mismatches are rarely benign. Alert on attempts to retrieve an uploaded path with an executable extension.

## Cross-References

- [`threat-modeling-stride.md`](threat-modeling-stride.md) — finding every trust boundary; Tampering control mapping.
- [`owasp-top-ten.md`](owasp-top-ten.md) — Injection, Broken Access Control (semantic ownership checks; SSRF as an access-control concern), and Software and Data Integrity Failures (deserialization).
- [`authentication-authorization.md`](authentication-authorization.md) — IDOR/BOLA, the access-control side of semantic validation.
- [`secure-design-principles.md`](secure-design-principles.md) — fail securely, complete mediation.
- [`secure-logging.md`](secure-logging.md) — sanitizing untrusted data at the log sink.
