envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-23T05:28:07Z

# Verify-drift on concurrent ledger writes — 4-plan dispatch held (module-budget-campaign-completion)

Step 4 entry (`phase_handshake verify --phase 3-outline --strict`) returned
`status: error, error: main_checkout_dirtied_during_plan` with 2 newly-dirty
paths, both under `.plan/orchestrator/process-compliance/` (`epic.md`,
`status.json`). Baseline at 3-outline capture was `main_dirty: 0`.

## Provenance

Both paths are operator-ledger state: the concurrent process-compliance session
is reconciling this plan's own filed findings (drain/archive/status updates)
while this plan runs. Phase-3-outline's contract restricts it to
`.plan/local/plans/module-budget-campaign-completion/**`; it cannot write the
orchestrator tree. Zero phase-authored paths in the drift set.

## Disposition applied

Per `planning-outline.md` Step 4 ("Stop on status: drift"), the phase-4-plan
dispatch was NOT issued. No transition, no metrics call, no new phase state.
This is the third filing in the ledger-churn family (after Issue 2 post-init
assertion and the 2-refine gate refusal, process-compliance findings 001/002):
the same absolute-cleanliness shape now fires at the verify gate, and here the
dirt arrives *during* the run from a concurrent session, so no amount of
pre-phase reconciliation by this plan can prevent recurrence.

## Suggested rule improvement (spans two seams)

1. Scope both the porcelain assertions AND the handshake `main_dirty`
   invariant to non-ledger paths (exclude `.plan/orchestrator/**`,
   symmetric with the `.plan/local/**` untracked exemption), or compare
   before/after within the dispatch and refuse only on newly-appeared
   non-ledger paths.
2. Alternatively, document a quiesce rule: concurrent ledger reconciliation
   pauses while a plan sits at a phase boundary. Without one of these, plans
   running alongside an active orchestrator session park at every gate.

## Recovery needs operator disposition

Options: (a) quiesce the concurrent ledger session, then this plan re-verifies
and dispatches phase-4-plan; (b) extend the earlier explicit override to cover
this verify-drift gate (advance with the 2 ledger paths named); (c) park the
plan. No orchestrator file will be touched without that disposition.
