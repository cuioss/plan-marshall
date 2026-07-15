# Adversarial-Refute: The Quality Verify Profile

This standard defines the **adversarial-refute** methodology the quality verify profile applies during the [findings-pipeline](../../ref-workflow-architecture/standards/findings-pipeline.md) verify stage. It is the verify-skill body that the `verification_profile: quality` producer declaration resolves to: when a producer that participates in the verify stage emits a candidate quality, structural, or documentation finding, the orchestrator's verify pre-stage loads this standard in-context and runs the refute procedure below over each pending finding before domain triage ever sees it.

This standard is the persona-code-reviewer's implementation of the [`ext-point-verify`](../../extension-api/standards/ext-point-verify.md) contract as a verify profile — the quality counterpart to the persona-security-expert's `security` profile. The contract owns the stage placement, the producer `verification_profile` declaration, the runtime invocation parameters, and the `rejected` resolution semantics — this document does NOT restate them; it documents only the cognitive methodology the stage applies for the `quality` profile.

The methodology is **adversarial by design**: the default posture toward a candidate finding is doubt, not acceptance. A finding earns its place in the triage queue only by *surviving* an honest attempt to disprove it. The burden is on the finding to demonstrate it is a genuine defect worth a human decision, not on the reviewer to demonstrate it is not.

## Why a Refute Pass Before Triage

A producer's raw quality findings are candidate signals, not confirmed defects. An LLM-reasoned review, simplification, or documentation pass over-reports by construction: it flags a *style preference* as if it were a correctness defect, flags a piece of structure as *surplus* without confirming nothing load-bearing depends on it, and flags a reference as *drifted* without confirming the reference is actually stale rather than already-correct. Sending those candidates straight to triage forces the triage stage (FIX / SUPPRESS / ACCEPT) to absorb the false-positive load — and a FIX decision on a non-defect is wasted work (or an actively harmful edit that removes load-bearing structure), while a SUPPRESS decision on a non-defect pollutes the suppression record with noise.

The refute pass moves false-positive elimination upstream of triage, where it belongs: a refuted finding closes `rejected` (a terminal, non-pending, non-blocking resolution) and never reaches triage. Only confirmed findings — those that survive refutation — flow on to `ext-triage-*` for the FIX / SUPPRESS / ACCEPT decision.

## Refute Procedure

For each candidate quality finding, attempt to **refute** it — to construct the strongest honest argument that it is NOT a genuine defect. Work through the refutation lenses below in order; a finding is refuted the moment any lens conclusively disproves it, and confirmed only when no lens can.

1. **Defect vs preference — is the observation a genuine defect, or a style preference?**
   Distinguish a real correctness, maintainability, or contract defect from a matter of taste. A finding that reports a genuine problem — a broken invariant, a resource leak, a swallowed error, a violated documented contract, a duplicated source-of-truth — is a defect. A finding that merely restates a stylistic inclination the codebase does not mandate (naming cadence, brace placement, "I would have factored this differently", an equally-valid alternative structure) is a preference, not a defect, and is refuted. Anchor the distinction in an enforceable standard or a documented convention wherever one exists; a finding that cannot be tied to any standard beyond the reviewer's taste is refuted as a preference.

2. **Surplus vs load-bearing — is the flagged structure actually removable, or does something depend on it?**
   For a finding that flags structure as redundant, dead, or over-engineered (the simplification producer's characteristic finding), trace what depends on the flagged structure before accepting that it is surplus. A branch, parameter, abstraction, or file is only surplus when nothing — no caller, no test, no extension point, no documented contract, no runtime configuration path — relies on it. If a consumer, a covering test, a declared interface, or a not-yet-obvious call path depends on the flagged structure, it is load-bearing and the finding is refuted. (A dependency that is itself dead — an unreached caller, a skipped test — does NOT rescue the structure; that is a genuine surplus and the finding survives.)

3. **Drift real vs already-correct — is the documentation/reference claim a genuine drift, or a false positive?**
   For a finding that flags a document, cross-reference, count, code sample, or link as stale or inconsistent (the doc-verify producer's characteristic finding), confirm the drift against the current source of truth before accepting it. A reference is drifted only when it genuinely disagrees with what it points at — a count that no longer matches, a link whose target moved or was removed, a code sample that no longer compiles or contradicts the current API, a described behavior the implementation no longer exhibits. A finding that flags a reference which, on inspection, still matches its target — the "drift" is a misread, the link resolves, the count is current — is a false positive and is refuted. Verify against the actual target, not against the finding's assertion about the target.

4. **Severity sanity — does the claimed severity survive scrutiny?**
   A finding may be a genuine defect but carry a mis-scaled severity (e.g. a `critical` flag on a cosmetic doc nit, or a `warning` on a data-loss bug). Severity mis-scaling does NOT refute the finding — the defect is real — but the refute pass records the corrected severity so the surviving finding reaches triage with an accurate severity. Use this lens only to adjust a confirmed finding, never to reject a real one.

Each refutation decision — and the lens that drove it — is logged to `decision.log`, so the rejection record is auditable.

## Confirm vs Reject

The refute procedure produces exactly one of two verdicts per finding:

| Verdict | When | Outcome |
|---------|------|---------|
| **Confirmed** | No refutation lens conclusively disproves the finding: the observation is a genuine defect rather than a preference (lens 1), the flagged structure is load-bearing-free surplus (lens 2), and any documentation claim reflects a real drift (lens 3). | The finding is left `pending` so the existing triage stage (`ext-triage-*`) picks it up unchanged for the FIX / SUPPRESS / ACCEPT decision. Lens 4 may have adjusted its severity. |
| **Refuted** | Any lens conclusively disproves the finding: the observation is a style preference, the flagged structure is load-bearing, or the documentation claim is a false positive on an already-correct reference. | The finding closes with the terminal resolution `rejected` per the [`ext-point-verify`](../../extension-api/standards/ext-point-verify.md) contract — non-pending, never reaches triage, never contributes to an invariant gate's blocking count. |

**Decision rule — refute only on a conclusive disproof.** The adversarial posture is *attempt* refutation, not *assume* it. A finding is rejected ONLY when a refutation lens conclusively establishes it is not a genuine defect. When refutation is inconclusive — the reviewer cannot prove the observation is mere preference, cannot confirm the flagged structure is truly unreferenced, or cannot rule out that a reference is genuinely drifted — the finding is **confirmed and flows to triage**. Doubt resolves in favor of the finding's survival: it is safer to send a possible-false-positive to triage (where it can still be SUPPRESSed or ACCEPTed with a recorded rationale) than to silently `reject` a real defect that then never reaches a human decision. The burden of proof is on the *rejection*, not on the confirmation.

## Related Specifications

- [`ext-point-verify.md`](../../extension-api/standards/ext-point-verify.md) — The verify extension-point contract this standard implements as the `quality` verify profile (stage placement, producer `verification_profile` declaration, `rejected` resolution)
- [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — The producer → store → verify → triage → gate pipeline the verify stage extends
- [`../../persona-security-expert/standards/adversarial-refute.md`](../../persona-security-expert/standards/adversarial-refute.md) — The sibling `security` verify profile this standard mirrors
