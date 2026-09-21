envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=landing
created=2026-07-30T11:50:04Z

## What landed

**PLAN-02 — A Multi-Resolver Derivation Seam, With Provenance on Every Answer** (PR #1067,
branch `feature/resolver-ext-point-seam`, head `405b05f069141ccb8367da57d90e958f89668a51`).

The `ext-point-derivation-resolver` extension point now exists: internal-dependency edge
derivation is a resolver seam rather than an inline coordinate join, every answer carries
provenance, and the multi-resolver merge is a first-class deterministic component.

Surfaces touched:

- `script-shared/scripts/extension/extension_base.py` — resolver base contract
- `extension-api/scripts/extension_discovery.py` — resolver discovery
- `extension-api/scripts/_derivation_merge.py` — new multi-resolver merge component
- `extension-api/standards/ext-point-derivation-resolver.md` + `extension-contract.md`
- `doc/concepts/code-intelligence.adoc`, `extension-architecture.adoc`, `README.adoc`
- tests: `test_extension_base_derivation_resolver.py`,
  `test_derivation_resolver_discovery.py`, `test_derivation_merge.py`

Planning shape: deep lane, escalated on `cross_cutting`, `execution_profile=full`,
confidence 98.5, scope `multi_module`, track `complex`.

## Gate outcomes

All finalize gates green: pre-push quality-gate (1 bundle + whole-tree, test-compile +
module-tests), plugin-doctor clean (2 skills gated), pre-submission-self-review clean
(117 candidates examined), simplify 0 edits/0 findings, security-audit 0 edits/0 findings,
architecture-refresh tier-0 clean with no descriptor delta, ci-verify all checks green,
sonar-roundtrip 0 new-code issues, lessons-housekeeping 0 removed / 0 promoted /
7 retained.

## Residue the epic should track

1. **Latent defect the plan removed, worth remembering as a shape.** The pre-seam
   coordinate join was last-write-wins over Maven coordinates. The fixture corpus in the
   tree contains a deliberately duplicated `com.example:auth-service` coordinate
   (`legacy/auth-service/pom.xml`), so the pre-seam join silently dropped a module. The
   seam plus its characterization fixtures now pin that as a real, enumerated case. Any
   future resolver added to this seam inherits the obligation to be duplicate-coordinate
   safe.

2. **Review coverage on #1067 was 1-of-3, not 3-of-3.** Filed separately as a `finding`
   in this inbox. A green finalize on this PR is not evidence that the configured review
   bots saw the diff.

3. **Three consecutive phase-5-execute dispatches were cut off by transient API errors**
   (HTTP 500, 529, 529). Each time disk state was verified before re-dispatch rather than
   blind-retried; no work was lost and no work was duplicated. No action owed — recorded
   because it is the third-party-instability cost of a deep-lane multi-deliverable plan,
   not a defect in the plan or the tooling.

## Candidate lessons emitted alongside this landing

- `candidate-lesson`: a cited call site is a SAMPLE, not an enumeration — three instances
  inside this one plan, one of them inside a plan whose own Overview flagged the trap.
- `candidate-lesson`: a centralizing refactor can silently widen a lazy contract into an
  eager one.
