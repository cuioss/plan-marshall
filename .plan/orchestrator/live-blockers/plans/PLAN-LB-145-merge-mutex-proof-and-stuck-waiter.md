# PLAN-LB-145: The merge dispatch proves the plan holds the merge mutex, and a waiter held behind a retained entry is told why and how to leave

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-145-merge-mutex-proof-and-stuck-waiter.md` and is queued as one row file, `queue/PLAN-LB-145.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged by the analyze drain of 2026-11-11 from `lessons-routing` finding 084 (graded high by the operator in the 2026-11-10 drain of that
> epic's inbox; two reports from the pm-mcp-core plan `plan-v2-86-core-store-tests-b`, PR 301). Grounded against `main` at `280e6c404` by a
> read-only leaf, with the orchestrator re-reading the merge dispatch, the liveness mapping and the live-worktree predicate. Every Done-when
> below fails at `280e6c404` unless it is a stated hold. No Sonar. No token or measurement work.

## Objective

A plan can merge without holding the cross-plan merge mutex, and a waiter can be held behind a queue entry for its whole wait with nothing
telling it why. `pre_merge_gate merge` runs four checks and then enqueues; the only reader of the mutex's admission result is prose in
`branch-cleanup.md`, so a run that chains the enqueue after an `admission=blocked` answer merges anyway (the report that opened this
finding). Separately, `queue-list` calls an entry `not_live` while the admission prune keeps it because its worktree still has git plumbing,
so the operator sees a dead holder and the waiter sees a blocked queue. This plan makes the merge dispatch ask for the proof and makes the
retained entry visible, with a named exit.

## Deliverables

1. **`pre_merge_gate merge` refuses a plan that does not provably hold the merge mutex.**
   - The gate reads the lock holder through the lock module's own reader and refuses, with a new named error code beside
     `merge_candidate_not_gated`, unless the holder is this plan. A lock held by another plan, an absent lock and an unreadable lock file
     are three distinct refusals: the last fails closed, and none of them calls the CI merge verb. The check runs after the invocation
     refusal and before any provider read, so a plan that does not hold the mutex is named without paying for a participation fetch.
   - The refusal carries the holder it read (or `none` / `unreadable`), the plan id it asked about and the remedy
     (`merge_lock acquire`, then read `admission`).
   - The call site in `phase-6-finalize/standards/branch-cleanup.md` states that the gate asks, so the prose loop stays the way to WAIT and
     is no longer the only net. Under `merge_hold_window: pre_merge_only` the acquire still happens at the Pre-Merge Gate; the gate's check
     runs after it.
   - Decide at outline, and record in the PR: whether the lane's own direct enqueue (`runbook-lane/SKILL.md`, HYPOTHESIS below) is in this
     check's scope. This spec's default is that it is not: the lane merges through its own gates, and `plan-orchestrator/workflow/land.md`
     enqueues a ledger-only pull request with no plan barrier on purpose.
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer

   *Done when:* each of these fails at `280e6c404`: `merge()` with no lock file returns the new refusal and the merge-runner stub is not
   called; with the lock held by another plan it returns the same code naming that holder; with an unreadable lock file it returns the
   refusal and not a dispatch. These hold at `280e6c404`: `merge()` with the lock held by this plan dispatches exactly as before and
   returns the same keys; the invocation refusal, the findings gate, the head binding and the participation gate keep their order and
   their codes.

2. **A waiter held behind a retained entry is told which entry, why it is retained and how to leave.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `queue-list` reports, for each entry, why admission keeps it: today `liveness` comes only from `git-workflow locate-plan-checkout`
     (`not_live` when no checkout holds the plan) while the admission prune keeps an entry whose worktree carries a `.git` marker or a live
     plan directory. A new field names the retention (the marker that keeps it) beside `liveness`, so the two readings cannot disagree
     silently.
   - The `blocked` / `not_fifo_front` admission reply names the entry in front, its liveness, its retention reason and the exit
     (`merge_lock dequeue --plan-id {front}`), so a waiter does not poll to its budget against an entry that will never leave on its own.
   - Decide at outline, and record in the PR: this spec's default keeps the protection of a mid-recovery worktree (an auto-reclaim of a
     holder whose git plumbing is intact steals a live recovery) and does NOT add a time-based expiry; it discloses and names the exit.
     A bounded expiry is a separate decision for the operator.

   *Done when:* each of these fails at `280e6c404`: with a queue entry whose plan has no checkout but whose worktree directory holds a `.git`
   marker, `queue-list` reports a retention reason for it; the `not_fifo_front` reply for the next waiter names that entry and the
   `dequeue` command. These hold at `280e6c404`: the same entry with no marker and no plan directory is pruned and the next waiter is
   admitted in the same attempt; a holder with a live worktree is still not auto-reclaimed.

3. **The documents and the pins say what the gate and the verbs do.**
   - Skills: pm-plugin-development:plugin-architecture
   - Persona: documenter
   - `manage-locks/SKILL.md` and `branch-cleanup.md` state the proof the gate asks for, the retention field and the exit; the sentence in
     `branch-cleanup.md` that admits abandoned waiters with a plan directory in the worktree are kept (about L125) states the field and the
     exit instead of the bare hazard.
   - A doc-contract test pins each statement in the section that states it, with a control that plants the old sentence.

   *Done when:* the doc-contract test passes on the changed documents and fails on a planted copy of the old sentence, for each pinned
   document; it fails at `280e6c404` because the documents state neither the proof nor the retention field.

Split guard: three deliverables, one theme (the merge mutex). D1 is the gate, D2 the queue verbs, D3 the sweep; D1 and D2 share no function
and can ship in either order.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- Fail closed: an unreadable lock file, an unreadable queue and an unanswerable liveness consult are never read as "holds the lock" or as
  "dead".
- One reader per concept: the gate asks the lock module for the holder and never re-derives the lock file's shape; `queue-list` and the
  admission prune name the retention from the same predicate (`holder_has_live_worktree`), not a copy of it.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so.
- The change touches an executor-visible script surface only if a verb or flag is added; the PR states whether an executor regeneration is
  owed.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `pre_merge_gate.merge()` runs `_invocation_refusal`, `_findings_refusal` (twice), `_head_binding_refusal` and `_participation_verdict`, then `build_merge_args` and the merge runner, and reads no merge lock — read at `phase-6-finalize/scripts/pre_merge_gate.py` L1796-1886; a content sweep for `merge_lock` finds 73 files and neither this one nor `runbook_lane.py` nor `runbook-lane/SKILL.md` is among them
- OBSERVED: `queue-list` reports `not_live` exactly when `git-workflow locate-plan-checkout` answers `not_found` — read at `manage-locks/scripts/merge_lock.py` § `_entry_liveness`, L1712-1719
- OBSERVED: `holder_has_live_worktree` is true for a `.git` marker or a live plan directory under `worktrees/{holder}`, and its docstring says the FIFO prune retains a waiter whose worktree is genuinely live — read at `manage-locks/scripts/_locks_core.py` L185-248
- HYPOTHESIS: an entry retained by that marker blocks every waiter as `not_fifo_front` for the whole budget, with no time-based expiry, and `budget-reclaim` and `release --require-stale` refuse it as `holder_not_provably_dead` — confirm/refute at `manage-locks/scripts/merge_lock.py` § `run_acquire`, § `run_budget_reclaim`, § `run_release` (leaf read, L1523-1542, L1820-1830, L2091-2100; verify-at-outline)
- HYPOTHESIS: an entry with NO marker is pruned and the next waiter is admitted in the same attempt, so the report that opened this finding (`not_live`, `not_found`, blocked for 240 s) is reproducible only with a live marker the report does not state — confirm/refute at `manage-locks/scripts/merge_lock.py` § `_prune_dead_waiting` and § `run_acquire` (leaf read, L501-520, L567-575, L1590-1602; verify-at-outline)
- HYPOTHESIS: `runbook-lane/SKILL.md` section 7 enqueues with `ci pr merge-queue` directly, with no mutex acquire and no `pre_merge_gate` — confirm/refute at `runbook-lane/SKILL.md` § 7 (leaf read, about L915-920; not re-read by the orchestrator)
- HYPOTHESIS: the lock file records only the plan id, `release` unlinks whenever the caller's plan id equals it, and a re-entrant `acquire` returns `already_held` for any caller with that id, so the proof this plan adds is a plan-id proof and a second session of the same plan passes it — confirm/refute at `manage-locks/scripts/merge_lock.py` § `_try_atomic_create`, § `run_release`, § `run_acquire` (leaf read, L922-941, L1510-1511, L1935-1952; `lessons-routing` finding 054 filed the ownership side and its disposition was not read here)
- HYPOTHESIS: `branch-cleanup.md` L101-128 is the only reader of the `admission` result, and L125 already admits the abandoned-waiter hazard — confirm/refute at `phase-6-finalize/standards/branch-cleanup.md` (leaf read of lines 1-180 and the diff; the file is large)
- Verify-first clause: before scoping D2's retention field, read `run_queue_list`'s emission and `run_acquire`'s `blocked` reply and record which fields each already carries; a field that exists is reused, not added.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — `merge`, the new refusal (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — `run_queue_list`, `_entry_liveness`, the `blocked` reply, a read-only holder query if none exists (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py` — `holder_has_live_worktree` reused, and the retention reason if it is derived here (D2; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the merge call site, about L101-128 (D1, D3)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` (D1)
- OBSERVED: `test/plan-marshall/manage-locks/test_merge_queue_list.py` and `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_live_worktree_reclaim_guard.py` (D2)
- HYPOTHESIS: a new doc-contract test module for D3 beside the existing `manage-locks` tests; its path is named at outline

## Dependencies and Sequencing

- Depends on: none. Sequence after PLAN-LB-144.
- Overlaps with: PLAN-LB-144 on `phase-6-finalize/scripts/pre_merge_gate.py` and `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` (two files, so an overlap prompt is due at emit); PLAN-LB-144 edits `_participation_refusal` and this plan edits `merge`, which share no function. Name functions and not lines at outline.
- Adjacent to: `lessons-routing` finding 054 (ownership keyed on the plan id alone) — D1's proof is only as strong as that identity; the finding's own disposition was not read here, and this plan does not change the lock file's identity. The lane's direct enqueue and `land.md`'s deliberate exemption are named above and stay out of scope unless the outline decides otherwise.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-145-merge-mutex-proof-and-stuck-waiter.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
