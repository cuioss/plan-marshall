# PLAN-112: The finalize ceremony pre-filter dropped the security audit on a 47-file code change

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-29 from inbox `one-coherent-automated-review-contract-012` (PLAN-92 / PR #1041).
> ⛔ **A security gate was silently removed from a large code change. Treat as high severity.**

## Objective

The finalize ceremony pre-filter dropped the **security audit** from a **47-file code change**,
gated on a **stale `change_type`**. The gate did not fail — it was never selected, so nothing
reported its absence. Make ceremony selection read a live signal, and make a dropped security step a
**loud, recorded outcome** rather than a silent omission.

## Why this is severe, stated precisely

A dropped *observability* step costs information. A dropped **security audit** on a 47-file change
means the change shipped without the check that exists to catch exactly what a large diff hides.
⚠ **And it is the second confirmed consequence of stale-classification input** — PLAN-101 already
established that the same predicate family drives the execution POSTURE, where `minimal` drops
sonar-roundtrip, automatic-review **and the security audit** by a documented dominance rule.
⇒ **Two independent paths now reach "security audit not run".** This plan owns the ceremony
pre-filter path; PLAN-101 owns the lane/posture path. **They are NOT the same defect and must not be
merged** — but D1 must read PLAN-101's findings before scoping, because a fix that addresses only
one path leaves the other live.

## Deliverables

1. **D1 — GATE (mutates nothing): establish which signal the pre-filter reads and when it goes
   stale.** Determine where `change_type` is computed, when it is frozen, and why a 47-file change
   presented as something the pre-filter could drop the security step for. ⛔ **Read PLAN-101's D1
   verdict first** — if the two paths share a predicate, say so explicitly rather than fixing twice.
2. **D2 — the pre-filter reads a live signal, or declares it cannot.** A selection decision taken
   against a frozen or absent classification is not a decision. Where a live read is impossible at
   that point in the lifecycle, the step must **fail toward inclusion**, not omission.
3. **D3 — a dropped security-class step is LOUD.** Omission of a security-class ceremony step is
   recorded as an explicit, operator-visible outcome with the gating reason named — never a silent
   absence from the step list. ⚠ **This deliverable stands even if D1 finds the classification was
   technically correct**: the absence must be visible either way.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) A large multi-file code change retains the
   security audit. (b) A stale/absent `change_type` fails toward inclusion. (c) A dropped
   security-class step emits its reason. (d) The population of security-class steps is
   **derived**, not a hardcoded list.

## Claim Labels

- OBSERVED (message-supplied, PLAN-92 / #1041): the security audit was dropped on a 47-file code
  change, gated on a stale `change_type`.
- OBSERVED (orchestrator-verified, epic ledger): PLAN-101's dominance-rule finding — `minimal`
  posture drops sonar-roundtrip, automatic-review and the security audit.
- HYPOTHESIS: the ceremony pre-filter and the posture predicate share a common classification input —
  confirm/refute at D1 (verify-at-outline). **If they DO share it, this plan may reduce to D3 plus a
  fold into PLAN-101; if they do not, all four deliverables stand.**
- Verify-first clause: re-read the ceremony pre-filter at HEAD. ⚠ **PLAN-101 is IN FLIGHT and edits
  the classifier surface** — re-baseline rather than scoping against a moving seam. Verify by SYMBOL.

## Expected Surface

- HYPOTHESIS: the finalize ceremony pre-filter in `phase-6-finalize` (verify-at-outline)
- HYPOTHESIS: the `change_type` producer — `manage-status` change-type heuristic (verify-at-outline)
- OBSERVED: `recipe-security-audit` is the dropped step's owner (read-only reference)

## Dependencies and Sequencing

- Depends on: ⚠ **PLAN-101's D1 verdict** (launched). Not a hard block — D1 here can start — but D2
  must not land before PLAN-101's classifier verdict is known.
- Overlaps with: ⛔ **PLAN-60 `in-house-gate-ci-parity`** and **PLAN-52** both touch finalize gates.
  Re-check disjointness before pairing. **PLAN-111** touches the finalize comment barrier — adjacent,
  probably disjoint, verify.
- Adjacent to: `code-intelligence-substrate` scope-derivation work — different epic; **check across
  the boundary**, per-epic disjointness does not see it. ⛔ **ID CORRECTION (2026-07-29):** this line
  previously cited **PLAN-61**, which exists in **neither** epic's `status.json`, and the
  attribution to the sibling is **itself unverified** — this epic's own stale generated START-HERE
  block still listed PLAN-61 as ITS OWN queue row. Candidate successor by slug is **PLAN-125**
  (`outline-plan-scope-derivation-integrity`). ⚠ **Both the successor identity AND the cross-epic
  attribution are inferred, not confirmed** (carve-out bars reading another epic's tree) —
  **re-resolve against the sibling queue by SLUG, not by number.** ⚠ This correction landed while this plan was already LAUNCHED, so it did **not** reach
  the running plan's ingested `request.md`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-112-ceremony-prefilter-dropped-the-security-audit.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
