> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-045`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-066: The retrospective reads a record that is not yet written

epic: truthful-signals
workstream: WS-01

> Staged plan spec — ready for `/plan-marshall` hand-off. Staged at the 2026-08-08 inbox drain
> from six converging candidate-lessons across three separate plans, plus the PR #1115 landing.

## Objective

`plan-retrospective` runs at finalize order 995; `record-metrics` writes `metrics.md` at 998.
The retrospective therefore reads a partially-written record and publishes conclusions about
it. This is already known as an ordering gap — what PR #1115 established is that the
consequence is **correctness, not completeness**: the retrospective published two specific
false figures that reached the operator report as facts. This plan makes the retrospective
refuse an artifact its writer has not produced, rather than reading it early and reporting
the reading.

## Deliverables

1. Make a retrospective read of a not-yet-written artifact **refuse** rather than return
   partial content — the consuming check reports `unavailable` with the reason, never a
   number derived from a partial file.
2. Reconcile the two disagreeing phase-6 token ledgers, or state in the record that neither
   is authoritative and that the union is a floor.
3. Regenerate `metrics.md` after a loop-back, or mark it explicitly stale — a record frozen
   before 6-finalize must not present itself as final.
4. Stop the retrospective's session capture from overwriting the plan's execution
   `session_id`.
5. Make `compile-report` fail loudly when it drops a section, and not delete the evidence it
   dropped.

Five deliverables — under the ~6 split guard, but **close to it**. Rationale for proceeding
unsplit: all five are one write-order contract over one artifact set, and splitting them would
put D1 and D3 in different plans while they govern the same file. If outline finds D4/D5
separable without touching D1's seam, split there.

## Claim Labels

- OBSERVED: the ordering is 995 before 998 — carried in this epic's ledger as a known-open
  item after #1080, and reconfirmed by the #1115 landing.
- OBSERVED: the false figures — #1115's retrospective reported `metrics.md` rendering the
  6-finalize row as `-` and a plan total of `1,438,440` ⇒ "2.01× the headline". The on-disk
  file reads `3,635,563 (mixed)` and `5,157,173 (n=5/6)`. Both read first-party at the landing
  analysis; see `landings/PLAN-TRUTH-042.md`.
- OBSERVED: two ledgers disagree and neither is a superset — from
  `lesson-retirement-fails-open-003`: `execution_log` 9 rows / 1,386,494 tokens vs
  `metrics-dispatch-boundaries-6-finalize.toon` 11 rows / 2,108,919; union 12 rows /
  2,163,290, **and the union is itself a floor**. ⚠ These counts are the filer's, measured on
  ONE plan — re-derive before pinning a test.
- OBSERVED: `metrics.md` is frozen before 6-finalize and never regenerated after a loop-back —
  from `merge-queue-enqueue-does-not-take-002`.
- OBSERVED: order-995 placement makes the coverage check structurally unmeasurable — from
  `a-rule-that-is-green-because-it-examined-nothing-003`.
- OBSERVED: retrospective session capture overwrites the plan's execution `session_id` — from
  `a-rule-that-is-green-because-it-examined-nothing-001`.
- OBSERVED: `compile-report` drops the dispatch-boundaries section **and then deletes the
  evidence** — from `a-rule-that-is-green-because-it-examined-nothing-008`.
- HYPOTHESIS: `compile-report`'s silent omission is a regression of PLAN-51
  (`retrospective-compile-report-silent-omit`, shipped #1009) rather than an uncovered path —
  confirm/refute by reading #1009's landed guard against the current dropping site
  (verify-at-outline). ⛔ **Establish which before scoping D5** — a regression and a gap take
  different fixes.
- Verify-first clause: the finalize order numbers (995 / 998) must be re-read from the live
  step registry at outline. This epic has already recorded one over-broad retirement that
  rested on un-rechecked order arithmetic; do not inherit the numbers from this spec.

## Expected Surface

- OBSERVED: `plan-marshall:plan-retrospective` — the 995 step and its artifact reads
- OBSERVED: `plan-marshall:manage-metrics` — `metrics.md` generation, `record-dispatch-boundary`
- HYPOTHESIS: the finalize step registry that assigns 995/998 (verify-at-outline)
- HYPOTHESIS: `compile-report` section assembly and its evidence cleanup (verify-at-outline)

## Dependencies and Sequencing

- ⛔ **SERIALIZE AFTER `PLAN-TRUTH-055`** — 055 owns the metrics record's representation of a
  re-entered phase and touches `manage-metrics` directly. This plan touches the same module for
  D2/D3. **055 is already emitted; do not pair these two.**
- Adjacent to `PLAN-TRUTH-045` (dispatch audit) — 045 owns whether the *checks* examine a real
  population; this owns whether the *record they read* exists yet. Cite, do not merge.
- Adjacent to `PLAN-TRUTH-050` (the operator report is an evidence surface the inbox cannot
  see) — same finalize tail, different artifact.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-066-the-retrospective-reads-a-record-that-is-not-yet-written.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
