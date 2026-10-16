# PLAN-LB-53: A halt stays a halt, and an operator decision stays the operator's

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
>
> **Restructured 2026-10-15** (operator instruction: OpenCode quality first; high and critical
> only). The phase-time deliverable (former D3: finalize time booked to execute across
> loop-backs, PLAN-LB-31, -39, -42) was dropped as medium — `settled.md` § "Dropped 2026-10-15".
> The file name keeps the original slug. **Each deliverable is its own outline deliverable; do not
> merge them.**

## Objective

Two behaviours recurred on consecutive OpenCode landings (PLAN-LB-31, -39, -42):

- **A halt that does not halt.** A post-dispatch guard records `failed` and the main context logs
  "halted", then improvises a recovery the workflow does not document (`session_move` on OpenCode)
  and retries. PLAN-LB-31 recovered a failed refine dispatch this way; PLAN-LB-39 did it at
  create-pr (2026-10-14T02:30).
- **A content conflict that never reaches the operator.** On PLAN-LB-39 the Conflict-Severity
  Classifier reported `overlap_with_content_conflict … needs_user`; branch-cleanup still told the
  operator "No rebase or force-push will happen — the merge queue rebases" (13:50), then asked them
  to wait for a queue the PR could not enter (14:08); the conflict surfaced at 16:27 and was
  hand-resolved, rebased and force-pushed without a new question.

## Deliverables

1. **A recorded halt ends the step.** When a dispatch guard or step gate records `failed` /
   `halted`, the only continuations are the ones the workflow names for that outcome (retry with
   its documented bound, loop-back, or an operator question). The step's next script call after a
   halt is refused unless it is one of those, and the refusal names them. Undocumented harness
   recovery verbs (e.g. OpenCode `session_move`) are not among them unless a workflow documents
   them with their preconditions.
   - A leaf that returns `escalate_ask` hands the decision to the operator. The main context asks
     the question and may not choose an option itself. PLAN-LB-42's root answered a CI-timeout
     `escalate_ask` ("Keep waiting") at 2026-10-15T09:39:52 without asking.

   - After the operator reports a problem (e.g. "#1778 has build bailure (not green)"), the main
     context takes no remedial action the operator did not choose; it states the options and asks.
     PLAN-LB-47 re-ran the failed CI check unasked, which let auto-merge proceed.
   - A refused phase transition (handshake drift) is never overridden by the main context:
     `phase_handshake capture --override` requires an operator answer recorded with it
     (`phase-lifecycle.md:83-84`). PLAN-LB-60's root overrode a 5→6 drift refusal with its own
     reason.
   - The option the operator selected is executed as worded. PLAN-LB-56's operator selected "Wait
     another 600s" for the review bots, and the root ran a CI wait instead.

   *Done when:* a test records a halted create-pr step and reads a refusal for a re-run that is not
   a named continuation; a named continuation passes; a step resolution recorded after an
   `escalate_ask` without a logged operator answer is refused.

2. **`needs_user` from the conflict classifier always becomes an operator question before any
   rebase, push or queue wait.** Branch-cleanup reads the classifier verdict before composing its
   question; with `needs_user` the question states the conflict (files, base) and its options —
   never "no rebase will happen". A rebase or force-push after the question requires the
   operator's answer to name it, and the pre-push gate runs on the rebased head before the push
   (with PLAN-LB-55 D1's push refusal as the backstop).

   *Done when:* a test feeds `overlap_with_content_conflict` / `needs_user` into branch-cleanup and
   reads a question naming the conflicting files and no merge-queue wait; a test reads the
   force-push refused when the operator's answer did not authorize it.

Split guard: two deliverables.

## Claim Labels

- OBSERVED: PLAN-LB-39 root logged "post-dispatch guard recorded failed and halted" at create-pr, then called `tools.opencode.session_move` and retried (2026-10-14T02:30, OpenCode DB `ses_ec9968164ffeRdYIgaux9dNEOC`, delegated agent).
- OBSERVED: PLAN-LB-31 recovered a failed refine dispatch with an improvised `session_move` (`landings/PLAN-LB-31.md` § Metrics and Anomalies).
- OBSERVED: PLAN-LB-39 `decision.log` L282 and L365 "running rebase SKIPPED, the merge queue rebases"; the transcript at 16:27:38–16:29:38 shows `worktree-rebase-to`, two raw `git rebase --continue`, `force-push-with-lease` (orchestrator-read).
- OBSERVED: the classifier reported `overlap_with_content_conflict … needs_user` before the 13:50 question (delegated agent).
- OBSERVED: PLAN-LB-42's root picked an option for a leaf's `escalate_ask` at 2026-10-15T09:39:52 with no operator question (delegated agent, OpenCode DB `ses_ec1e528a8ffelWqi96aLAe4yua`).
- HYPOTHESIS: the classifier's verdict is available to branch-cleanup through its "one-stop read" (`decision.log` L282) — confirm where it is read (verify-at-outline).

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/` — halt refusal, conflict routing (verify-at-outline) (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — step-gate halt state (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — halt and conflict tests (D1, D2)

## Dependencies and Sequencing

- Depends on: none. After PLAN-LB-55 is preferable for D2 (its push refusal is the backstop).
- Overlaps with: PLAN-LB-55 on phase-6-finalize scripts and the push path. The gate will ask.

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
