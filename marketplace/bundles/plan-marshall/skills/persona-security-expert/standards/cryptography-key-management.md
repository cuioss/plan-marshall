# Cryptography and Key Management

Cryptography fails far more often through *misuse* than through broken primitives: a sound algorithm wired up with a reused nonce, a hardcoded key, or a deprecated mode is as exploitable as no encryption at all. This document is the single authoritative home for algorithm selection (symmetric, asymmetric, hashing, signatures), key lifecycle (generation, storage, rotation, destruction), envelope encryption, and TLS / secure-transport configuration. It owns the algorithm-authority and key-management rules; integration sites cross-reference it rather than restating them — [`secrets-handling.md`](secrets-handling.md) owns secret *storage and rotation operations* and defers algorithm choice here, and [`authentication-authorization.md`](authentication-authorization.md) owns *password hashing* (a deliberately distinct discipline — see "Hashing Is Not One Thing" below).

Source of record: OWASP Cheat Sheets ([Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html), [Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html), [Transport Layer Security](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html)), OWASP Top 10 **A04:2025 Cryptographic Failures**, and NIST [SP 800-57](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf) (key management), [SP 800-52](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-52r2.pdf) (TLS), [SP 800-131A](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar2.pdf) (algorithm transitions), and [FIPS 186-5](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-5.pdf) (digital signatures).

---

## Symmetric Encryption: Use Authenticated Encryption (AEAD)

**Maps to:** CWE-327 · OWASP A04 · ASVS V6

Encryption without integrity is a defect. A plain-confidentiality mode (CBC, CTR, and especially ECB) leaves ciphertext malleable: an attacker who can flip bits in transit alters the decrypted plaintext undetected, and padding-oracle attacks recover plaintext from CBC error behavior. ECB additionally leaks structure — identical plaintext blocks produce identical ciphertext blocks, so patterns survive encryption.

Mitigations:

- **Default to an AEAD construction**: AES-256-GCM or ChaCha20-Poly1305. Authenticated modes bind confidentiality and integrity in one operation and reject any tampered ciphertext before it is decrypted.
- **Never use ECB.** It is unconditionally unsuitable for more than one block of data.
- If a non-AEAD building block is unavoidable (legacy interop), apply **Encrypt-then-MAC** with an independent MAC key — never Encrypt-and-MAC or MAC-then-Encrypt. Prefer migrating the call site to AEAD.
- Treat CBC + PKCS#7 padding as legacy: A04:2025 explicitly lists CBC padding among the deprecated building blocks.

---

## IV / Nonce Management

**Maps to:** CWE-323 · CWE-329 · OWASP A04 · ASVS V6

For AEAD modes, the IV/nonce is the single most dangerous parameter. A nonce reused under the same key with GCM or ChaCha20-Poly1305 is catastrophic: it leaks the XOR of two plaintexts and — for GCM — exposes the authentication subkey, letting an attacker forge arbitrary authenticated ciphertexts. This is not a gradual degradation; one reuse can break the whole key.

Mitigations:

- Generate a **unique IV/nonce for every encryption operation** under a given key — even when the key itself is unchanged.
- For GCM, use a 96-bit nonce from a counter or a CSPRNG; never let a nonce repeat for the lifetime of the key.
- The IV/nonce is not secret and may be stored or transmitted alongside the ciphertext; uniqueness, not secrecy, is the requirement.
- Rotate the key well before the nonce space is at risk of collision (see "Key Lifecycle" — the data-volume rotation trigger).

---

## Randomness: CSPRNG Only

**Maps to:** CWE-330 · CWE-331 · CWE-338 · CWE-1241 · OWASP A04 · ASVS V6

Every key, IV, nonce, salt, and security token MUST come from a cryptographically secure pseudo-random number generator. A general-purpose PRNG (`java.util.Random`, Python `random`, JavaScript `Math.random`) is predictable: its output can be reconstructed from a handful of observed values, so a token generator built on one lets an attacker predict future session tokens or password-reset codes.

Mitigations:

- Use the platform CSPRNG: Java `java.security.SecureRandom`, Python `secrets`, Node.js `crypto.randomBytes()`, .NET `RandomNumberGenerator`, PHP `random_bytes()`.
- Never substitute a fast non-cryptographic PRNG for any value with a security role.
- Do not treat a UUIDv1 as random — it is derived from timestamp and MAC address and is guessable. Use UUIDv4 (CSPRNG-backed) or raw CSPRNG bytes where unpredictability matters.

---

## Hashing Is Not One Thing

**Maps to:** CWE-327 · CWE-916 · OWASP A04 · ASVS V6

Two distinct disciplines are routinely conflated. **Integrity / general-purpose hashing** answers "has this data changed?" and wants a *fast* collision-resistant hash (SHA-256, SHA-512, SHA-3). **Password hashing** answers "is this the right password?" and wants a *deliberately slow*, memory-hard, salted key-derivation function — using a fast hash for passwords is a vulnerability, because it lets an attacker brute-force a stolen hash database at billions of guesses per second.

Mitigations:

- **Integrity hashing**: SHA-256 / SHA-512 / SHA-3. Never MD5 or SHA-1 — both are collision-broken and unsuitable for any integrity or signature purpose.
- **Password hashing is owned by [`authentication-authorization.md`](authentication-authorization.md)** (Argon2id primary; scrypt / bcrypt / PBKDF2 fallbacks). Do not use a bare SHA-family hash for passwords; do not reimplement the password-storage parameters here.
- For keyed integrity, use HMAC-SHA-256, not a naive hash-of-key-concatenated-with-message.

---

## Asymmetric Encryption and Key Exchange

**Maps to:** CWE-326 · CWE-327 · OWASP A04 · ASVS V6

Asymmetric failures are usually about *inadequate key length* or *padding*. RSA below 2048 bits is factorable within reach of well-resourced attackers (CWE-326), and RSA with PKCS#1 v1.5 encryption padding is vulnerable to Bleichenbacher-style padding oracles.

Mitigations:

- Prefer **elliptic-curve cryptography** (Curve25519 / X25519 for key agreement) — equivalent strength at far smaller key sizes and with simpler, harder-to-misuse APIs.
- When RSA is required, use **≥ 2048 bits** (3072+ for data that must stay confidential past 2030) and **OAEP** padding for encryption — never PKCS#1 v1.5 encryption padding.
- Use ephemeral key agreement (ECDHE) for transport so each session has forward secrecy.

---

## Digital Signatures

**Maps to:** CWE-327 · CWE-347 · OWASP A04 · ASVS V6

A signature is only as trustworthy as its hash and algorithm. Signing over MD5 or SHA-1 lets an attacker craft a colliding document that carries a valid signature; verifying with a downgraded or attacker-chosen algorithm (the "alg: none" JWT class) bypasses the signature entirely.

Mitigations:

- Prefer **Ed25519 / Ed448 (EdDSA)**, or **deterministic ECDSA** ([RFC 6979](https://www.rfc-editor.org/rfc/rfc6979) — avoids the catastrophic ECDSA nonce-reuse failure), or **RSA ≥ 2048** with a SHA-2 hash.
- Never sign or verify with MD5 or SHA-1. Per FIPS 186-5, DSA is removed for signature *generation*.
- On verification, pin the expected algorithm; never let the message header dictate which algorithm (or whether any) is used.

---

## Key Lifecycle

**Maps to:** CWE-320 · CWE-321 · CWE-322 · OWASP A04 · ASVS V6

A key has a full lifecycle — generation, distribution, use, rotation, archival, and destruction — and a failure at any stage compromises everything the key protected. The dominant real-world failure is a hardcoded or plaintext-stored key (CWE-321 / CWE-320): once such a key is in a repo, an image layer, or a config file, it is exposed and cannot be quietly fixed because every artifact encrypted under it must be re-keyed.

Mitigations:

- **Generate** keys inside a FIPS 140-2/140-3 validated module (HSM or vetted library), seeded by a CSPRNG.
- **One key, one purpose.** A key used for encryption is not reused for signing; a data-encryption key (DEK) and the key-encryption key (KEK) that wraps it are fully independent.
- **Rotate** on any of: confirmed or suspected compromise; the end of the key's cryptoperiod ([NIST SP 800-57](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf)); a data-volume threshold (e.g. the birthday bound for 64-bit-block ciphers, ~64 GB under one key); or the algorithm being deprecated. Prefer decrypt-and-re-encrypt over leaving stale ciphertext under a retired key.
- **Never store a key in plaintext**, and **never store a key alongside the data it protects** — filesystem-resident keys for database-resident data, so one flaw (SQL injection, directory traversal) cannot disclose both the lock and the contents.
- **Destroy** retired key material; do not let decommissioned keys accumulate as a latent breach surface.

---

## Key Storage and Hardware-Backed Protection

**Maps to:** CWE-321 · CWE-522 · OWASP A04 · ASVS V6

Where a key lives determines the blast radius of a host compromise. A key sitting in an environment variable is readable through `/proc/self/environ`, a crash dump, or a `docker inspect`; a key in a hardware-backed store never leaves the boundary in cleartext, so even full host compromise does not yield the raw key.

Mitigations:

- **Prefer a hardware security module or cloud KMS** — AWS KMS, Azure Key Vault, GCP Cloud KMS, or an on-prem HSM. The key performs operations inside the boundary; the application holds only a handle.
- For application-managed keys, use a **dedicated secrets manager** (Vault, Conjur) — never source control, never an environment variable for high-sensitivity key material. The secret-storage *operations* (centralization, least-privilege access, rotation automation, leak detection) are owned by [`secrets-handling.md`](secrets-handling.md); this section owns the *algorithmic and lifecycle* requirements that storage must satisfy.
- Treat environment variables as acceptable only for low-sensitivity configuration, never for keys — see the environment-variable pitfall in [`secrets-handling.md`](secrets-handling.md).

---

## Envelope Encryption

**Maps to:** CWE-320 · OWASP A04 · ASVS V6

Encrypting large or numerous data items directly under a master key forces a full re-encryption on every rotation and concentrates risk in one key. **Envelope encryption** decouples the two: a per-item **data-encryption key (DEK)** encrypts the data, and a long-lived **key-encryption key (KEK)** encrypts the DEK; only the wrapped DEK is stored next to the data, while the KEK lives in an HSM/KMS.

Mitigations:

- Store the wrapped DEK with the ciphertext; store the KEK separately in hardware-backed storage.
- The KEK's strength must be **≥** the strength of every key it protects.
- When the KEK is derived from a user passphrase, derive it through a KDF (HKDF for high-entropy inputs; a password-hashing KDF for passphrases) so the passphrase can change by re-wrapping the DEK — no bulk data re-encryption required.
- Rotate the KEK by re-wrapping DEKs (cheap) rather than re-encrypting data (expensive).

---

## TLS and Secure Transport

**Maps to:** CWE-319 · CWE-326 · OWASP A04 · ASVS V9

Data in transit is a trust boundary. A downgrade to a legacy protocol (TLS 1.0/1.1, SSLv3) or a non-forward-secret cipher means a passive attacker who later obtains the server's private key can decrypt previously captured traffic, and an active attacker can strip TLS entirely if HSTS is absent.

Mitigations:

- **Default to TLS 1.3**; permit TLS 1.2 only for compatibility. **Disable TLS 1.0/1.1** ([RFC 8996](https://www.rfc-editor.org/rfc/rfc8996)) and all of SSLv2/SSLv3.
- Offer only **AEAD cipher suites** with **forward secrecy** (ECDHE / ffdhe — ffdhe2048+, x25519, secp384r1). Disable null, anonymous, export, and static-RSA/static-DH suites.
- Enforce **HSTS**, serve every page over TLS, and set the `Secure` flag on cookies so they are never sent in cleartext. (The HSTS response header and the broader security-header set are catalogued in [`owasp-top-ten.md`](owasp-top-ten.md) under A02 Security Misconfiguration.)
- **Never disable certificate verification** as a workaround. Certificate pinning is rarely worth its outage risk; if used, pin a leaf certificate or public key with backup pins on native mobile only — never pin a root CA, and never substitute "skip verification" for a pinning problem.

---

## Never Roll Your Own Crypto

**Maps to:** CWE-327 · OWASP A04 · ASVS V6

Custom cipher constructions, homemade key-derivation, and ad-hoc "obfuscation" are reliably broken. The failure mode is subtle: the construction appears to work (it round-trips), so the defect is invisible until an attacker exploits it.

Mitigations:

- Use vetted, maintained cryptographic libraries and high-level misuse-resistant APIs; do not assemble primitives by hand.
- Design for **defense in depth** — the system should remain safe even if one cryptographic control is later found weak (see [`secure-design-principles.md`](secure-design-principles.md)).
- Treat any of the following as a finding: hardcoded keys, reused IV/nonce, non-CSPRNG randomness, MD5/SHA-1, ECB, plain confidentiality without integrity, and any protocol that permits downgrade.

---

## Cross-References

- [`secrets-handling.md`](secrets-handling.md) — secret storage, rotation automation, dynamic secrets, and leak detection (defers algorithm and key-lifecycle authority to this document).
- [`authentication-authorization.md`](authentication-authorization.md) — password hashing (Argon2id and fallbacks) as the distinct slow-hash discipline.
- [`owasp-top-ten.md`](owasp-top-ten.md) — A04 Cryptographic Failures (this document's risk category) and A02 Security Misconfiguration (security headers, HSTS).
- [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md) — the in-transit trust boundary that TLS protects.
- [`secure-design-principles.md`](secure-design-principles.md) — defense in depth, fail securely, economy of mechanism (vetted-library reuse).
- Per-domain mechanics: [`pm-dev-java:java-security`](../../../../pm-dev-java/skills/java-security/SKILL.md) (`SecureRandom`, `char[]`/`byte[]` key handling) and [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md) (KMS / secret injection at the container boundary).
