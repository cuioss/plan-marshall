# Adversarial-Refute: The Security Verify Profile

This standard defines the **adversarial-refute** methodology the security verify profile applies during the [findings-pipeline](../../ref-workflow-architecture/standards/findings-pipeline.md) verify stage. It is the verify-skill body that the `verification_profile: security` producer declaration resolves to: when a producer that participates in the verify stage emits a candidate security finding, the orchestrator's verify pre-stage loads this standard in-context and runs the refute procedure below over each pending finding before domain triage ever sees it.

This standard is the persona-security-expert's implementation of the [`ext-point-verify`](../../extension-api/standards/ext-point-verify.md) contract as a verify profile. The contract owns the stage placement, the producer `verification_profile` declaration, the runtime invocation parameters, and the `rejected` resolution semantics — this document does NOT restate them; it documents only the cognitive methodology the stage applies for the `security` profile.

The methodology is **adversarial by design**: the default posture toward a candidate finding is doubt, not acceptance. A finding earns its place in the triage queue only by *surviving* an honest attempt to disprove it. This is the security-review counterpart to the scientific null hypothesis — the burden is on the finding to demonstrate it is a genuine, reachable defect, not on the reviewer to demonstrate it is not.

## Why a Refute Pass Before Triage

A producer's raw security findings are candidate signals, not confirmed defects. An automated or pattern-driven security pass over-reports by construction: it flags a dangerous *sink* without proving an untrusted source actually reaches it, flags an input as unvalidated without checking whether an upstream boundary already validated it, and flags a pattern that *resembles* an exploit without confirming the pattern is exploitable in this context. Sending those candidates straight to triage forces the triage stage (FIX / SUPPRESS / ACCEPT) to absorb the false-positive load — and a FIX decision on a non-defect is wasted work, while a SUPPRESS decision on a non-defect pollutes the suppression record with noise.

The refute pass moves false-positive elimination upstream of triage, where it belongs: a refuted finding closes `rejected` (a terminal, non-pending, non-blocking resolution) and never reaches triage. Only confirmed findings — those that survive refutation — flow on to `ext-triage-*` for the FIX / SUPPRESS / ACCEPT decision.

## Refute Procedure

For each candidate security finding, attempt to **refute** it — to construct the strongest honest argument that it is NOT a genuine, exploitable defect. Work through the refutation lenses below in order; a finding is refuted the moment any lens conclusively disproves it, and confirmed only when no lens can.

1. **Reachability — is the sink actually reachable with untrusted input?**
   Trace backward from the flagged sink to its sources. A dangerous sink (a subprocess call, a deserialization, an `eval`, an SQL string interpolation, a `innerHTML` write) is only a defect when an **untrusted** source can reach it. If every value that flows into the sink is a compile-time constant, a developer-controlled literal, or a value derived solely from trusted internal state, the sink is not exploitable and the finding is refuted. Apply the trust-boundary model in [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md) to decide which sources are untrusted.

2. **Upstream validation — is the input already validated or sanitized before the sink?**
   When an untrusted source does reach the sink, check whether a validation, sanitization, or encoding step on the path between source and sink already neutralizes the threat. An input that is allow-list-validated, type-coerced at a parse boundary, or contextually encoded before it reaches the sink is no longer the exploit vector the finding claims. A finding that ignores an existing, correct upstream guard is refuted. (A guard that is incomplete, bypassable, or applied in the wrong context does NOT refute the finding — that is a real defect.)

3. **Exploitability — is the flagged pattern a genuine exploit or a benign look-alike?**
   Some patterns trip a producer's heuristic without being exploitable: a `subprocess` call with a fully static argument vector and `shell=False`; a regex that *looks* catastrophic but operates on length-bounded trusted input; a "hardcoded secret" that is a well-known public test fixture or an example placeholder. Map the candidate to the concrete threat it would represent under the relevant OWASP category ([`owasp-top-ten.md`](owasp-top-ten.md)) and the STRIDE property it would violate ([`threat-modeling-stride.md`](threat-modeling-stride.md)). If no concrete, in-context exploit can be constructed, the finding is refuted as a benign look-alike.

4. **Severity sanity — does the claimed severity survive scrutiny?**
   A finding may be a genuine defect but carry a mis-scaled severity (e.g. a `critical` flag on an issue reachable only with already-privileged access, or on a defense-in-depth gap behind a correct primary control). Severity mis-scaling does NOT refute the finding — the defect is real — but the refute pass records the corrected severity so the surviving finding reaches triage with an accurate severity. Use this lens only to adjust a confirmed finding, never to reject a real one.

Each refutation decision — and the lens that drove it — is logged to `decision.log`, so the rejection record is auditable.

## Confirm vs Reject

The refute procedure produces exactly one of two verdicts per finding:

| Verdict | When | Outcome |
|---------|------|---------|
| **Confirmed** | No refutation lens conclusively disproves the finding: an untrusted source reaches the sink (lens 1), no upstream guard neutralizes it (lens 2), and a concrete in-context exploit exists (lens 3). | The finding is left `pending` so the existing triage stage (`ext-triage-*`) picks it up unchanged for the FIX / SUPPRESS / ACCEPT decision. Lens 4 may have adjusted its severity. |
| **Refuted** | Any lens conclusively disproves the finding: the sink is unreachable with untrusted input, an existing upstream guard neutralizes it, or no concrete exploit can be constructed. | The finding closes with the terminal resolution `rejected` per the [`ext-point-verify`](../../extension-api/standards/ext-point-verify.md) contract — non-pending, never reaches triage, never contributes to an invariant gate's blocking count. |

**Decision rule — refute only on a conclusive disproof.** The adversarial posture is *attempt* refutation, not *assume* it. A finding is rejected ONLY when a refutation lens conclusively establishes it is not a genuine, reachable, exploitable defect. When refutation is inconclusive — the reviewer cannot prove the sink is unreachable, cannot confirm an upstream guard is complete, or cannot rule out an exploit — the finding is **confirmed and flows to triage**. Doubt resolves in favor of the finding's survival: it is safer to send a possible-false-positive to triage (where it can still be SUPPRESSed or ACCEPTed with a recorded rationale) than to silently `reject` a real defect that then never reaches a human decision. The burden of proof is on the *rejection*, not on the confirmation.

## Related Specifications

- [`ext-point-verify.md`](../../extension-api/standards/ext-point-verify.md) — The verify extension-point contract this standard implements as the `security` verify profile (stage placement, producer `verification_profile` declaration, `rejected` resolution)
- [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — The producer → store → verify → triage → gate pipeline the verify stage extends
- [`input-validation-trust-boundaries.md`](input-validation-trust-boundaries.md) — The trust-boundary and untrusted-source model applied in refutation lenses 1 and 2
- [`owasp-top-ten.md`](owasp-top-ten.md) — The OWASP category mapping applied in refutation lens 3
- [`threat-modeling-stride.md`](threat-modeling-stride.md) — The STRIDE property mapping applied in refutation lens 3
