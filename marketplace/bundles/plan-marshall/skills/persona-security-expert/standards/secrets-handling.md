# Secrets Handling

Secrets — API keys, database passwords, OAuth tokens, certificates, encryption keys — are the highest-value targets in any system. This document covers externalizing secrets, secret-manager integration, rotation, dynamic secrets, the environment-variable pitfall, and hardcoded-credential detection. It is the **cross-cutting** home for these principles; per-domain mechanics (e.g. Java `char[]` over `String`, container secret injection) live in the respective domain security skills and xref back here.

Source of record: [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html), with key-lifecycle guidance from [NIST SP 800-57](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf).

---

## The Foundational Rule: Never Store Secrets in Source or Config

Hardcoding a secret in source code or version-controlled configuration is a root-cause vulnerability from which all other failures derive. Once committed to git, a secret is exposed to anyone with repo access and **persists indefinitely in history even after deletion**. Attacker automation scans new public commits within minutes. The scale is severe: tens of millions of hardcoded secrets are added to public GitHub repositories each year, and private repos are several times more likely than public ones to contain them.

Corollary: resolve every secret from external configuration at runtime; never bake it into the artifact, the image, or the repo.

---

## Centralize in a Dedicated Secrets Manager

Establish a primary secrets manager and standardize the interaction and lifecycle patterns around it:

- **HashiCorp Vault** — self-managed, multi-cloud, supports dynamic secrets.
- **AWS Secrets Manager** — managed, AWS-native.
- **Azure Key Vault** — managed; combines secrets + keys + certificates (note: vault-level permission granularity means using separate vaults per workload).
- **Google Secret Manager** — managed, GCP-native.

Centralization enables consistent enforcement of the full lifecycle — creation, rotation, revocation, auditing, and access control — across all teams. For multi-cloud, prefer cloud-agnostic solutions to avoid lock-in, and maintain a **secondary backup secrets manager** holding the root credentials of the primary system.

---

## Least Privilege for Secret Access

Apply [least privilege](secure-design-principles.md) to every user and service that touches the secrets system:

- Configure default **deny-all**, then grant explicitly.
- Scope access at the **individual-secret** level, not system-wide — a microservice should read one database credential, not the entire secrets engine.
- Assign a unique identity to each application/microservice.
- Implement just-in-time (JIT) access for human operators with automatic expiration; revoke offboarded access within minutes.

---

## Rotation and Dynamic Secrets

**Automate rotation** — manual maintenance increases both leakage risk and human error. Three patterns, in increasing preference:

1. **Gradual / dual-credential rotation** — provision the new credential, propagate to all consumers, verify it is active, drain old connections, then revoke the old one.
2. **Scheduled rotation** — time-based automatic updates.
3. **Dynamic creation (preferred)** — generate a temporary credential per session/TTL with automatic revocation.

**Dynamic secrets** eliminate credential reuse and shrink blast radius: Vault's database secrets engine creates a unique user with a random password per request (set a short TTL — e.g. 1 hour for production DBs), so credentials never live long enough to accumulate rotation debt. For CI/CD, **OIDC federation** (GitHub Actions OIDC, AWS IRSA) and **SPIFFE/SPIRE** workload identity remove stored secrets entirely — the act of calling from a specific process on a specific node, plus OS-level attestation, *is* the identity, resolving the "secret zero" bootstrap problem. Keep JWT-SVID TTLs small (5–10 minutes).

**Lifetimes** ([NIST SP 800-57](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf)): symmetric encryption keys ≤ 2 years; asymmetric signing keys 1–3 years; TLS certificate keys 90 days–1 year. Rotation compliance remains poor in practice — a majority of leaked secrets remain active long after exposure, which is why dynamic/short-lived secrets are the strategic direction.

---

## The Environment-Variable Pitfall

Environment variables are **not** a safe transport for high-sensitivity secrets in container/orchestration environments. Concrete leak vectors:

- Kubernetes env vars injected from Secrets are visible via `kubectl describe pod` and captured by most logging agents.
- Docker stores env vars in plaintext, readable via `docker inspect`; `ARG`/`ENV` instructions persist in image history.
- `.env` files routinely end up in version control via `git add .`.
- Spawned child processes inherit all parent env vars (violating least privilege); on Unix, any user can read `/proc/self/environ`.
- App crashes may dump all env vars to logs or a remote error service.

Secure alternatives: orchestrator-mounted volumes, in-memory sidecar injection (Vault Agent sidecar), the External Secrets Operator, or SPIFFE/SPIRE workload identity. Never bake secrets into an image via `Dockerfile ENV`/`ARG`. (Environment variables remain acceptable for *low-sensitivity configuration*, not credentials — the contextual reconciliation of the 12-factor recommendation against modern container-security analysis.) Container-specific secret injection mechanics live in [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md).

---

## Encrypt Secrets at Rest and in Transit

Never store or transmit a secret in plaintext: encrypt it at rest and rely on TLS in transit. The *algorithm choice* for both — which AEAD cipher, which approved key lengths, which TLS version and cipher suites — is owned by [`cryptography-key-management.md`](cryptography-key-management.md); apply its rules here rather than restating them. The secrets-management-specific points are operational:

- **Kubernetes Secrets are base64-encoded, not encrypted** — a base64 string is not a security control. Enable etcd encryption-at-rest so the stored object is actually protected.
- **Store the encryption keys separately from the encrypted secrets** so one disclosure does not yield both (the key-separation rule, detailed in [`cryptography-key-management.md`](cryptography-key-management.md)).

---

## Hardcoded-Credential Detection

No single scanner is sufficient — academic benchmarks show only 18–76% overlap between tools' true positives, so run more than one. A layered framework:

1. **Pre-commit hooks** (Gitleaks, TruffleHog, git-secrets, talisman) — catch most accidental leaks, but can be bypassed with `--no-verify`, so not sufficient alone.
2. **CI/CD blocking gate** — catches bypassed pre-commit hooks; use verification-enabled tools.
3. **Full git-history scanning** — not just HEAD; legacy leaks live in deleted commits and dangling objects.
4. **OIDC federation for CI/CD** — eliminates the static credentials that get scanned for in the first place.
5. **Self-identifying token formats** (known prefixes + checksums) — significantly improve scanner accuracy.
6. **Periodic re-scan with liveness verification** — confirm whether detected credentials are still active.

Tool selection: Gitleaks (fast, TOML-configurable, best for CI gates) versus TruffleHog (live API verification, best for incident response and history sweeps). AI-assisted commits leak at roughly double the baseline rate.

---

## Audit Logging and Incident Response

Record who requested each secret (system, role, identity) and why; log approval/rejection; track expiration and attempted re-use of revoked credentials; monitor authn/authz errors. Retain queryable logs ≥ 90 days. Alert on anomalies: unexpected IPs, unusual locations, excessive failures. (Logging mechanics — and the rule that secrets must never appear in logs — are in [`secure-logging.md`](secure-logging.md).)

**Incident response order when a secret leaks:** (1) **Rotate immediately** — do not wait for investigation; attackers scan within minutes. (2) Review audit logs (CloudTrail, GCP Audit) for unauthorized use. (3) Assess blast radius. (4) History scrubbing is secondary — *rotation eliminates the security risk; history cleaning only addresses compliance*. Maintain tested break-glass credentials in a secondary encrypted system.

---

## Cross-References

- [`cryptography-key-management.md`](cryptography-key-management.md) — algorithm authority for encrypting secrets at rest/in transit, key storage, and the key-lifecycle rules secret rotation implements.
- [`secure-design-principles.md`](secure-design-principles.md) — least privilege, secure by default (secrets in a secret manager by default).
- [`owasp-top-ten.md`](owasp-top-ten.md) — A04 Cryptographic Failures (hardcoded credentials), A08 Software and Data Integrity Failures (supply-chain/CI-CD secret handling).
- [`secure-logging.md`](secure-logging.md) — the never-log-secrets rule.
- Per-domain memory handling and injection: [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md) (Java `char[]`/`byte[]` over immutable `String`).
