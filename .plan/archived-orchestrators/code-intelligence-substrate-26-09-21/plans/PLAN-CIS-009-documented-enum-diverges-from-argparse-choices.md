# PLAN-CIS-009: A documented enum that omits 5 of 11 values, while asserting the rest are rejected

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

`record-dispatch-boundary`'s argparse enum accepts **11** `termination_cause` values.
`manage-metrics/SKILL.md` documents **6** — and states emphatically that the flag is *"Required —
missing or unrecognised values are rejected as script errors (there is no implicit fallback)"*.

⛔ **A reader who trusts the SKILL would conclude the other five are rejected. They are accepted.** The
documentation is not merely incomplete; it makes a **positive false claim about the rejection
behaviour**, which is the failure mode that turns a doc gap into a wrong action.

⭐ **The sharp edge**: the two values one observed plan's boundary files actually contained —
`step_complete` (all 6 rows of its 6-finalize file) and `task_batch_complete` (its 4-plan file) — are
**both undocumented**. So 7 of that plan's 10 recorded rows carried a `termination_cause` its own SKILL
says cannot exist.

The drift compounds downstream: `plan-retrospective/references/logging-gap-analysis.md`'s
`DISPATCH_TERMINATION_CAUSE` rule instructs the analyst to report *"the per-cause distribution over the
canonical value set"* and then enumerates only the same 6 — so an analyst following the reference
literally emits a distribution that **omits the only causes present**.

## Deliverables

1. **Correct the enum** in `manage-metrics/SKILL.md` to the real accepted set, and correct the
   "rejected as script errors" sentence so it describes actual behaviour.
2. **Correct the consumer** — `plan-retrospective/references/logging-gap-analysis.md`'s
   `DISPATCH_TERMINATION_CAUSE` canonical value set, so it matches argparse.
3. **Pin it structurally** — a test asserting the documented value list **equals** the parser's
   `choices` tuple. ⛔ **Derive both sides**: parse the documented list out of the markdown and read
   `choices` from the parser; a hand-copied expected-list in the test reproduces the defect in the
   guard. Model it on the dispatch-roster closure test, which already pins a set this way.
4. **Sweep for siblings** — other places where a prose enum sits alongside an argparse `choices` list.
   ⛔ **Derive the population; do not trust this spec's two named sites.** Record "none found" as a
   legitimate complete outcome.

Four deliverables.

## Claim Labels

- **OBSERVED (first-party, from the PLAN-10 run's own artifacts)**: that run's boundary files contained
  `step_complete` and `task_batch_complete`, and `finalize-step-lessons-housekeeping` surfaced lesson
  `2026-07-27-08-006` during the same run.
- **HYPOTHESIS (message-supplied, NOT orchestrator-verified)**: the argparse enum has exactly 11 values
  and the SKILL documents exactly the first 6. ⛔ **This orchestrator did NOT read either file.**
  Confirm/refute at `manage-metrics/scripts/` § the `record-dispatch-boundary` parser's `choices` and
  `manage-metrics/SKILL.md` § the `termination_cause` documentation (verify-at-outline). **The counts
  6 and 11 are the message's arithmetic — re-derive them before quoting them anywhere.**
- **HYPOTHESIS**: sibling prose-vs-`choices` drift exists elsewhere. An asserted *possibility*, resolved
  by enumeration (deliverable 4).

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` and the
  `record-dispatch-boundary` argparse definition under that skill's `scripts/` (verify-at-outline).
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/logging-gap-analysis.md`
  (verify-at-outline).
- **OBSERVED**: tests under `test/plan-marshall/manage-metrics/**`.

**Disjointness:** `manage-metrics` + `plan-retrospective` (references only). ⛔ **`plan-retrospective`
is the same bundle as PLAN-CIS-008, PLAN-CIS-012 and PLAN-CIS-013** — sequence against all three, never pair. ✅
`manage-metrics` is free: PLAN-10 shipped as #1059.

## Dependencies and Sequencing

- **Depends on**: none. Small and surgical.
- ⚠ **Reconcile with the EXISTING lesson `2026-07-27-08-006`** (manage-metrics, termination-cause doc
  drift) rather than filing a parallel one. ⛔ **That lesson already existed and was surfaced by
  `lessons-housekeeping` during the very run that rewrote this file — and was dismissed as "unrelated"
  because it was judged against the plan's deliverable scope rather than against the file the
  deliverable was about to rewrite.** This plan closes it; the recurrence is evidence the lesson needs
  *enacting*, not restating.

## Provenance

Staged 2026-07-29 from `end-phase-replace-not-accumulate-009` at the PLAN-10 landing. ⭐ The Boy Scout
observation is worth carrying into the outline: deliverable 1 of PLAN-10 rewrote `manage-metrics/SKILL.md`
**end to end** — the `end-phase` idempotency line, the `phase-boundary` paragraph, the `generate` output
block, the `metrics.toon` example — **while the stale enum sat in the same document, in the section
describing the very artifact whose accounting the plan was fixing.** Two compounding causes: the enum
grew by five values and the prose count was never re-derived (the count-prose-staleness archetype), and
a whole-file rewrite passed over it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-009-documented-enum-diverges-from-argparse-choices.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
