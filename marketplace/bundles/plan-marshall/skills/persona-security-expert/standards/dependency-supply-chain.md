# Dependency and Supply-Chain Security

Modern applications are mostly other people's code: direct and transitive dependencies, base images, build tools, and CI/CD actions. The supply chain is the path that code travels from a third-party author to your running system, and every hop is an attack surface. SolarWinds (a compromised vendor update reaching roughly eighteen thousand organizations), the xz/liblzma backdoor (a maintainer-trust long-game injected during the distribution build), and the first self-propagating npm worm show the pattern: the attacker never touches your repository — they compromise something you trust and let your own build pull it in. This document is the single authoritative home for dependency vetting, lock-file discipline, SBOM generation, provenance verification, typosquat/confusion defense, CI/CD pipeline hardening, and the supply-chain threat model. Integration sites cross-reference it; they do not restate its controls.

Source of record: OWASP Top 10 **A03:2025 Software Supply Chain Failures**, OWASP Cheat Sheets ([Software Supply Chain Security](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html), [CI/CD Security](https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html), [npm Security](https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html)), [OWASP CICD-SEC Top 10](https://owasp.org/www-project-top-10-ci-cd-security-risks/), [OWASP SCVS](https://owasp.org/www-project-software-component-verification-standard/), [SLSA v1.0](https://slsa.dev/), [Sigstore](https://www.sigstore.dev/), and [CycloneDX](https://cyclonedx.org/).

---

## Dependency Vetting and Continuous Composition Analysis

**Maps to:** CWE-1104 · CWE-1395 · OWASP A03 · ASVS V10

A dependency with a known vulnerability is the most common supply-chain failure — Log4Shell and the Struts2 remote-code-execution flaw both exploited widely-used components that downstream teams had pulled in years earlier and never re-checked. A dependency is not a one-time decision; a component that was clean at adoption becomes vulnerable the day a CVE lands against it.

Mitigations:

- **Vet before adoption** — evaluate every external component (maintenance health, maintainer count, transitive footprint, license) and treat each new integration as a risk requiring explicit approval.
- **Run software composition analysis continuously** in CI, not just at adoption — OWASP Dependency-Check, npm/yarn audit, OSS Index, RetireJS, Bundler Audit. Map installed components to known-vulnerability feeds (NVD, OSV, CISA KEV) on every build.
- **Remove unused dependencies** (CWE-1104) — every retained dependency is attack surface, and an unused one is pure liability.
- **Patch on a risk basis**, not a fixed calendar — a KEV-listed flaw in an internet-facing component is not a "next quarter" item. Where an upgrade is infeasible, apply a virtual patch (WAF rule, config mitigation) until migration lands.

---

## Lock Files and Integrity Pinning

**Maps to:** CWE-1104 · CWE-829 · OWASP A03 · ASVS V10

If the build resolves "latest" at install time, the bytes that ship are whatever the registry served that minute — a window a compromised or hijacked package walks straight through. Pinning to a verified version with an integrity hash closes that window: the build fails rather than silently installing a substituted artifact.

Mitigations:

- **Commit the lock file** (`package-lock.json`, `yarn.lock`, `Pipfile.lock`, `poetry.lock`, `go.sum`) and configure the package manager to *enforce* it (`npm ci`, not `npm install`) so installs are reproducible and offline-verifiable.
- **Pin to specific, pre-vetted versions**; never auto-pull `latest` or an unbounded range for production builds.
- **Verify integrity** — the lock file's per-package hash must match the downloaded artifact; enable registry signature verification where the ecosystem supports it.
- **Run dependency install scripts in an isolated context** with no access to secrets — a malicious post-install script is a primary execution vector.

---

## Software Bill of Materials (SBOM)

**Maps to:** CWE-1395 · OWASP A03 · OWASP A08 · ASVS V10

You cannot respond to a supply-chain incident for a component you do not know you have. When the next "which of our services pulls in the backdoored library?" question arrives, the answer must be queryable in minutes, not reconstructed by hand — which means an inventory of direct *and transitive* dependencies, generated automatically and kept current.

Mitigations:

- **Generate an SBOM automatically at build time** — after dependency resolution, before packaging — capturing versions, checksums, and tool metadata for the full transitive graph. Tools: Syft, the CycloneDX CLI.
- **Choose the format by purpose**: CycloneDX is supply-chain / vulnerability-focused (the format Dependency-Track consumes); SPDX is license / compliance-focused.
- **Consume SBOMs continuously** — feed them into a platform (OWASP Dependency-Track) that correlates components against vulnerability databases over time, so a newly-disclosed CVE surfaces against an already-shipped build.
- **Sign and retain** SBOMs so they are tamper-evident and available for incident response against historical releases.

---

## Provenance and SLSA

**Maps to:** CWE-494 · OWASP A03 · OWASP A08 · ASVS V10

Knowing *what* is in a build is necessary but not sufficient; you also need to know *that the artifact was built the way you think it was*. Provenance is verifiable metadata about how an artifact was produced — the platform, the process, and the inputs — so a substituted or tampered build is detectable.

Mitigations:

- Target the [SLSA](https://slsa.dev/) Build track levels deliberately: **L1** = provenance exists (may be unsigned); **L2** = a hosted build platform emits platform-signed provenance; **L3** = strong isolation between build runs and unforgeable provenance (the signing key is inaccessible to the build steps themselves).
- **Generate provenance with a trusted builder** (e.g. the SLSA GitHub Actions builders) and **verify it on consumption** with the SLSA Verifier before an artifact is promoted or deployed.
- Know SLSA's scope: it addresses *build* integrity. It deliberately does **not** cover source compromise, malicious dependency *content*, registry compromise, or typosquatting — those are covered by the SCVS pedigree controls, pinning, and continuous SCA above.

---

## Artifact Signing

**Maps to:** CWE-494 · OWASP A03 · OWASP A08 · ASVS V10

A signature binds an artifact to an identity so a consumer can refuse anything unsigned or signed by the wrong party. Unsigned artifacts let an attacker who reaches the distribution path swap in their own build undetected (CWE-494, "download of code without integrity check").

Mitigations:

- **Sign components and validate signatures before use**; protect the signing infrastructure as a top-tier asset.
- Prefer **keyless, identity-based signing** ([Sigstore](https://www.sigstore.dev/) `cosign` via Fulcio short-lived certificates + the Rekor transparency log) — there is no long-lived private key to steal.
- **Verify against an expected identity, not merely "a valid signature"**: `cosign verify` with `--certificate-identity` *and* `--certificate-oidc-issuer` (all pairs must match); use `cosign verify-attestation` to validate in-toto provenance.

---

## Dependency Confusion, Typosquatting, and Hijacking

**Maps to:** CWE-1104 · OWASP A03 · ASVS V10

Three related name-based attacks: **dependency confusion** publishes a malicious *public* package reusing an internal package name, so a misconfigured resolver pulls the attacker's higher-version public copy instead of your private one; **typosquatting** registers a lookalike misspelling of a popular package; **maintainer hijacking** compromises a legitimate maintainer's account and ships malware in a trusted package's next release.

Mitigations:

- **Scope/namespace private packages** and configure the resolver to fetch internal names **only** from the internal registry — never let an internal name fall through to a public one.
- **Route external packages through an internal proxy / private repository** that mirrors pre-vetted versions, and commit the resolver configuration (`.npmrc`-style) so the policy is enforced for every developer and CI run.
- **Pin pre-vetted versions** (per "Lock Files" above) so a hijacked maintainer's new release does not auto-install, and run install scripts without secret access.

---

## CI/CD Pipeline Hardening

**Maps to:** CWE-1395 · OWASP A03 · ASVS V10

The build pipeline is privileged: it has source access, signing keys, deploy credentials, and the authority to ship. A compromised third-party action or an over-permissioned token turns the pipeline into the delivery mechanism for an attack (the CICD-SEC risk class).

Mitigations:

- **Pin third-party Actions / reusable workflows by full commit SHA**, never a mutable tag or branch — a tag can be repointed at malicious code. Scan for impostor commits (Zizmor, Harden-Runner).
- **Default `permissions: {}`** at the workflow level and grant the minimum scope per job; restrict the `GITHUB_TOKEN`; set `persist-credentials: false`.
- **Replace static credentials** (PATs, long-lived cloud keys) with **OIDC short-lived tokens / trusted publishing** (the secret-zero elimination detailed in [`secrets-handling.md`](secrets-handling.md)).
- **Use ephemeral, isolated, hermetic runners** destroyed after each build; run CI as non-root; segregate and restrict runner egress; never `docker --privileged`; keep pipeline configuration in version control.
- **Enforce separation of duties** ([`secure-design-principles.md`](secure-design-principles.md)): non-bypassable reviewed PRs, protected branches, signed commits, MFA across SCM/build, and a manual approval gate before production promotion. No single identity both writes code and ships it unobserved.

---

## Staged Rollout to Bound Blast Radius

**Maps to:** CWE-1357 · OWASP A03 · ASVS V10

Even a fully-vetted vendor update can be the compromised one (SolarWinds was signed and trusted). The residual control is to limit how far a bad update propagates before it is caught.

Mitigations:

- **Test compatibility before promotion**, then roll out in **stages / canaries** with a manual production approval gate, so a malicious or broken update reaches a small population first.
- **Monitor continuously after deploy** — supply-chain compromises often manifest as anomalous runtime behavior (unexpected egress, credential access) rather than a failed build.
- Assess your own and your suppliers' maturity against the [OWASP SCVS](https://owasp.org/www-project-software-component-verification-standard/) control families (inventory, SBOM, build environment, package management, component analysis, pedigree & provenance).

---

## Cross-References

- [`secure-design-principles.md`](secure-design-principles.md) — separation of duties and minimize-attack-surface as the design principles behind pipeline hardening and dependency minimization.
- [`secrets-handling.md`](secrets-handling.md) — OIDC federation / trusted publishing that removes static CI credentials, and the secret-zero bootstrap problem.
- [`owasp-top-ten.md`](owasp-top-ten.md) — A03 Software Supply Chain Failures (this document's category) and A08 Software and Data Integrity Failures.
- [`threat-modeling-stride.md`](threat-modeling-stride.md) — Tampering and the trust boundary that every dependency crosses.
- Per-domain mechanics: [`pm-dev-oci:oci-security`](../../../../pm-dev-oci/skills/oci-security/SKILL.md) (image provenance, base-image pinning, the OWASP Docker Top 10 supply-chain controls).
