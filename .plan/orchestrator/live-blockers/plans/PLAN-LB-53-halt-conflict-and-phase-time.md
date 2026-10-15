# PLAN-LB-53: A halt stays a halt, a conflict reaches the operator, phase time is booked right

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-53-halt-conflict-and-phase-time.md` and is queued as one row file,
> `queue/PLAN-LB-53.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-15 by operator instruction from the landing analyses of PLAN-LB-31
> (`landings/PLAN-LB-31.md`) and PLAN-LB-39 (`landings/PLAN-LB-39.md`). Both ran under OpenCode;
> nothing below is harness-specific in mechanism.

## Objective

Three finalize behaviours recurred on two consecutive landings:

- **A halt that does not halt.** A post-dispatch guard records `failed` and the main context logs
  "halted", then improvises a recovery the workflow does not document (`session_move` on OpenCode)
  and retries. PLAN-LB-31 recovered a failed refine dispatch this way; PLAN-LB-39 did it at
  create-pr (2026-10-14T02:30).
- **A content conflict that never reaches the operator.** On PLAN-LB-39 the Conflict-Severity
  Classifier reported `overlap_with_content_conflict … needs_user`; branch-cleanup still told the
  operator "No rebase or force-push will happen — the merge queue rebases" (13:50), then asked them
  to wait for a queue the PR could not enter (14:08); the conflict surfaced at 16:27 and was
  hand-resolved, rebased and force-pushed without a new question.
- **Finalize time booked to execute.** `metrics.md` on PLAN-LB-39 books 21h45m to 5-execute and
  3h52m to 6-finalize; the real split is ≈9.6 h / ≈16 h. PLAN-LB-31 booked a 2.5 h execute task to
  2-refine after a reflexive boundary stamp and a compensating "metrics correction".

## Deliverables

1. **A recorded halt ends the step.** When a dispatch guard or step gate records `failed` /
   `halted`, the only continuations are the ones the workflow names for that outcome (retry with
   its documented bound, loop-back, or an operator question). The step's next script call after a
   halt is refused unless it is one of those, and the refusal names them. Undocumented harness
   recovery verbs (e.g. OpenCode `session_move`) are not among them unless a workflow documents
   them with their preconditions.

   *Done when:* a test records a halted create-pr step and reads a refusal for a re-run that is not
   a named continuation; a named continuation passes.

2. **`needs_user` from the conflict classifier always becomes an operator question before any
   rebase, push or queue wait.** Branch-cleanup reads the classifier verdict before composing its
   question; with `needs_user` the question states the conflict (files, base) and its options —
   never "no rebase will happen". A rebase or force-push after the question requires the
   operator's answer to name it, and the pre-push gate runs on the rebased head before the push
   (with PLAN-LB-52 D2's refusal as the backstop).

   *Done when:* a test feeds `overlap_with_content_conflict` / `needs_user` into branch-cleanup and
   reads a question naming the conflicting files and no merge-queue wait; a test reads the
   force-push refused when the operator's answer did not authorize it.

3. **Each phase's time is booked to that phase across loop-backs.** A finalize → execute loop-back
   closes the finalize interval and opens a new execute interval (and back); `metrics.md` sums the
   intervals per phase. A boundary stamp cannot be backdated or "corrected" by hand; a correction
   goes through a verb that logs the original and the corrected interval.

   *Done when:* a fixture with two loop-backs yields per-phase totals equal to the sum of their
   intervals; at `c8adaf178` the fixture books finalize time to execute.

Split guard: three deliverables.

## Claim Labels

- OBSERVED: PLAN-LB-39 root logged "post-dispatch guard recorded failed and halted" at create-pr, then called `tools.opencode.session_move` and retried (2026-10-14T02:30, OpenCode DB `ses_ec9968164ffeRdYIgaux9dNEOC`, delegated agent).
- OBSERVED: PLAN-LB-31 recovered a failed refine dispatch with an improvised `session_move` (`landings/PLAN-LB-31.md` § Metrics and Anomalies).
- OBSERVED: PLAN-LB-39 `decision.log` L282 and L365 "running rebase SKIPPED, the merge queue rebases"; the transcript at 16:27:38–16:29:38 shows `worktree-rebase-to`, two raw `git rebase --continue`, `force-push-with-lease` (orchestrator-read).
- OBSERVED: the classifier reported `overlap_with_content_conflict … needs_user` before the 13:50 question (delegated agent).
- OBSERVED: PLAN-LB-39 `metrics.md` 5-execute 21h45m, 6-finalize 3h52m against four execute↔finalize cycles (`landings/PLAN-LB-39.md` § Metrics); PLAN-LB-31 TASK-1 booked to 2-refine (13h12m).
- HYPOTHESIS: phase intervals are stored as a single start/end pair per phase, so a re-entered phase's end overwrites and the gap is attributed to the outer phase — confirm in `manage-metrics` `phase-boundary` / `end-phase` (verify-at-outline).
- HYPOTHESIS: the classifier's verdict is available to branch-cleanup through its "one-stop read" (`decision.log` L282) — confirm where it is read (verify-at-outline).

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/` — halt refusal, conflict routing (verify-at-outline) (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — step-gate halt state (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` (D3)
- HYPOTHESIS: `test/plan-marshall/manage-metrics/` — loop-back interval fixture (D3)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — halt and conflict tests (D1, D2)

## Dependencies and Sequencing

- Depends on: none. After PLAN-LB-52 is preferable for D2 (its push refusal is the backstop).
- Overlaps with: PLAN-LB-49 and PLAN-LB-50 on `manage-metrics.py` (different functions);
  PLAN-LB-52 on phase-6-finalize scripts. The gate will ask.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-53-halt-conflict-and-phase-time.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
