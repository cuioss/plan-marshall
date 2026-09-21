envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T13:11:08Z

component=plan-marshall:manage-metrics
category=bug
created=2026-07-29
bundle=plan-marshall

# Reconcile record-step and record-dispatch-boundary into one accounting ledger

Two independent per-step token ledgers ran side by side for the whole finalize phase and disagree
without anything noticing:

- `manage-execution-manifest record-step` writes `(plan-marshall:manage-execution-manifest:record-step)`
  entries into `logs/decision.log` — **15 step rows** for this run.
- `manage-metrics record-dispatch-boundary` writes
  `work/metrics-dispatch-boundaries-6-finalize.toon` — **6 rows** for this run.

On the two steps BOTH ledgers recorded, they disagree by 41 and 43 percent:

| Step | record-step | dispatch-boundary | delta |
|------|------------:|------------------:|------:|
| `pre-submission-self-review` | 237,007 tok / 43 uses / 581,079 ms | 139,396 tok / 29 uses / 356,609 ms | -41% |
| `automatic-review` | 185,133 tok / 31 uses / 444,570 ms | 104,596 tok / 18 uses / 358,350 ms | -43% |
| `automatic-review` (2nd re-fire) | 140,838 tok / 34 uses | *(absent)* | -100% |

The populations also differ in kind, not just in size: `record-step` carries zero-valued rows for
the inline steps (`push`, `ci-verify`, `architecture-refresh`, `branch-cleanup`, all `0/0/0`) that
the boundary ledger has no concept of, while the boundary ledger carries a row at `07:36:42`
(80,537 tok) with no `record-step` counterpart at all.

There is no reconciliation step, no cross-check, and no consumer that reads both. Whichever a
consumer picks, it reads a confident number with no second opinion.

## Solution

Add a `manage-metrics reconcile` verb that unions the two ledgers by step key, emits a per-step
delta table, and fails loud (or emits a finding) when any shared step diverges beyond a small
tolerance or when a step appears in one ledger and not the other. Then make `generate` consume the
reconciled view rather than either raw ledger, so `metrics.md` reports one number with a stated
provenance instead of one of two silently-disagreeing numbers.

If the two ledgers are measuring genuinely different things (e.g. envelope-inclusive vs
envelope-exclusive accounting), that distinction must be named in both artifacts — an unlabelled
41 percent gap between two files that both look like "tokens for this step" is not a design, it is
a trap.

## Impact

This retrospective had to hand-reconstruct the plan's true token total from three sources
(`metrics.toon` phase rows, the post-loop-back boundary row `metrics.toon` never absorbed, and the
`decision.log` record-step sum) because no single artifact was trustworthy. That reconstruction is
exactly the deterministic work a script should own. Until it does, every token-economics figure the
epic quotes rests on an unexamined choice between two disagreeing producers.

## Evidence

- `logs/decision.log` — 15 `(plan-marshall:manage-execution-manifest:record-step)` entries,
  06:11:56 through 12:54:04.
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 6 rows.
- The three-row delta table above, computed from those two artifacts.
- `work/fragment-routing-decisions.toon` `cost_preview.actual_tokens: 1118350` — which is the
  `record-step` 6-finalize sum, i.e. a third consumer that silently picked one of the two ledgers.
