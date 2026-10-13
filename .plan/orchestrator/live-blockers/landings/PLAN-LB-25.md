# Landing Analysis: PLAN-LB-25 — Phase and merge gates

epic: live-blockers
workstream: WS-01
pr: #1751 (https://github.com/cuioss/plan-marshall/pull/1751)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-25.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-25-phase-and-merge-gates-012.md` (kind `landing`, `landing-check`
`complete: true`; surface delta `unmeasured`). Checked against:

- `ci pr queue-state --pr-number 1751`: `pr_state: merged`,
  `merge_commit_sha: 3ff307ddde6b723b5c8f5a51711e860ab074ade4`, merge-group run `success`.
- The merge as it fast-forwarded into the ledger worktree: 54 files, 5084 insertions, 631
  deletions (with the two dependency bumps #1743 and #1744 in the same range).
- A read-only review of commit 3ff307ddd against the spec by a delegated agent that ran nothing.

Not read by that review: the bodies of most new and modified tests (names and stats only, two
read), the `_invariants.py` diff, `manage-locks/SKILL.md`, the `manage-status/SKILL.md` diff,
several standards documents, executor registration of `pre_merge_gate`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 — the archive step reads the refusal | shipped, with a deviation (instruction only) | `archive-plan.md` STOP branch re-marks the step `failed` and skips the log and sweep; CLI test `test_archive_cli_refusal_is_a_status_error_with_exit_zero`; doc test `test_archive_plan_refusal_contract.py` |
| 2 — `normal_completion` is gated | shipped, plus an extra | `_cmd_lifecycle.py` `_COMPLETION_ASSERTING_ARCHIVE_REASONS`, casefolded match; exempt reasons report `findings_gate` and one WARNING line; an empty `--reason` is refused |
| 3 — a mechanical pre-merge gate | shipped (Shape A) | new `phase-6-finalize/scripts/pre_merge_gate.py`: `merge()` refuses a non-success verdict (265-271), fails closed unless it sees a measured `blocking_count == 0` (272-286), then calls the runner (296); `branch-cleanup.md` routes both merge verbs through it. It does not re-check required-bot completion (stated in the PR) |
| 4 — documents and docstrings | shipped | `phase-handshake.md`, `findings-pipeline.md`, two `SKILL.md`, `_cmd_lifecycle.py` docstrings, `_invariants.py` |
| 5 — admission wait without `sleep` | shipped, plus an extra | `merge_lock.py` `run_acquire --wait-seconds` loop (1446-1477), capped at 480 s; a new `dequeue` verb (`run_dequeue`, 1963) |
| 6 — landing wait | shipped, with a deviation | re-issues `pr wait-for-queue-settle` with one branch per `settle` value; a GitLab merge-train short-circuit; `merge_commit_sha` read from the PR (closes the item folded from PLAN-LB-29) |
| 7 — light-lane `pr_title` producer | shipped | `planning.md` step 2; (a) now uses `--allow-bare-transition`, fixing the `refine_bare_transition` half of #1697 |
| 8 — capture-source matrix | shipped | matrix in `planning.md`; `light-lane.md` persists `track=simple`; test derives the product set |
| 9 — lane-correct refusal | shipped | `_pr_title_missing_payload` shared by `capture` and `verify`, with `producer` and `remedy_command` |
| 10 — the lock is held across integrate | shipped, with an accepted residual | `integrate_into_main.py` releases only when it took the lock (`took_lock = action != 'already_held'`), with a 90 s bounded acquire and dequeue on refusal |

Realized surface against the declared one: outside the declaration — four standards documents,
about ten `manage-locks` tests and seven other test modules (three new); the declared
`test_no_standalone_sleep_in_wait_docs.py` shipped as `test_branch_cleanup_waits_no_sleep.py`.
Declared and not touched: `phase_handshake.py`, `ci_base.py`, `_cmd_merge_authorization.py` —
all three conditional on Shape B, so correct.

## What the plan achieved against its objective

- **Merge: enforced by a script**, failing closed on a failed query, an unrecognised verdict and
  an exception. The bare `ci pr safe-merge` / `merge-queue` verbs stay callable outside the gate;
  Shape A accepts that and only prose forbids it.
- **Archive: enforced by `manage-status`**, which refuses and moves nothing. Recording the step
  `failed` is an instruction an agent can skip; the worst outcome is a wrong step record, never a
  wrongly archived plan.
- **Waits: bounded inside scripts**, no standalone `sleep`.
- **Light lane: a documented producer step**; the invariant was not weakened.

## Accepted residuals (operator decision at the self-review round cap)

- **Lock ownership is keyed on `plan_id`.** `_attempt_acquire` returns `already_held` whenever
  the holder is the same plan (`merge_lock.py:1497-1498`), and `run_release` unlinks on the same
  test (1922-1939), so a second finalize session of the same plan is admitted at once and either
  session's release removes the other's lock. Needs two concurrent finalize sessions of one plan
  (a resumed session beside a live one); nothing prevents it. Low likelihood.
- **Release while not holding, on the landing-gate failure path.** After an unobserved enqueue
  the lock is released (`branch-cleanup.md:1562-1566`); landing-gate failure step 2 (1688-1693)
  then releases again unconditionally, against invariant 4 (line 120: a run not holding the lock
  dequeues, never releases). Harmful only together with the first. Very low likelihood.

## Metrics and Anomalies

- Tokens: 14,267,696. Wall 135,010 s (about 37.5 hours).
- Self-review used all five rounds and closed by operator override; each round on the
  merge-lock / integrate lifecycle found a new real defect (fixed in TASK-21..23).
- CI failed once on a root-level test guard (`test/test_harness_shape_guards.py`, rule R5) that
  the scoped module run never executes; the pre-push gate skipped the whole-tree run on
  `divergence_possible=false`. Second plan in a row (PLAN-LB-34 first).
- `verification-feedback` refused ci-verify's producer strings (`unknown_producer`); the
  orchestrator routed the CI failure itself.
- The `cuioss-review-bot` re-review matched a CodeRabbit review — the live confirmation of
  PLAN-LB-38 deliverable 3.
- Module-tests tier flipped per_task → orchestrator → per_task within one plan; 4 of 10 execute
  dispatches were hand-backs.
- Finalize dispatch-boundary rows stop at 08:35Z while finalize ran to about 15:54Z; all keyless
  — sixth landing.
- `archive-plan` pending. A `uv.lock` re-lock from the post-merge target regeneration is left
  uncommitted in the main checkout (caused by the ruff/mypy bumps, not by this plan).

## Collisions with plans in flight

- PLAN-LB-38 (running): the rate-window claim, wait, grace and wake code is unchanged, moved
  down by insertions (`_DEFAULT_WINDOW_SECONDS` now `merge_lock.py:357`, `_run_rate_window_wait`
  2325, grace and wake 2378-2416); items 7a (1381) and 7c(0) (1701) unchanged. The module
  paragraph "No mutating verb sleeps" was rewritten, and the `run_poll_delay` docstring (2461-2462)
  still cites the old heading.
- PLAN-LB-37 (running): `phase-6-finalize/SKILL.md` gained a `pre_merge_gate` row and block
  (2231-2285); five new and two modified tests under `test/plan-marshall/phase-6-finalize/`.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` 1751; `landing`; `plan_marshall_plan_id`
  lb-25-phase-and-merge-gates
- [x] epic.md queue annotation, Open Defects, drain recorded; PLAN-LB-26 folds
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- Session-scoped merge-lock ownership, with the landing-gate failure path fixed in the same change
  (lesson `2026-10-11-16-004`).
- Root-level test guards before push (lesson `2026-10-11-16-003`).
- The stale "No mutating verb sleeps" reference in the `run_poll_delay` docstring.
