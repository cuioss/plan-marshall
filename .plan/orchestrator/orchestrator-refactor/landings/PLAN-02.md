# Landing Analysis: PLAN-02 — Ledger decomposition and row vocabulary

epic: orchestrator-refactor
workstream: WS-01
pr: #1609

> Landing record for one shipped plan. Lives at `landings/PLAN-02.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Verified against `plans/PLAN-02-ledger-decomposition-and-row-vocabulary.md`, the merge
commit `21578e44774642f2dcfc89c27a90322be65c9a80` (confirmed as an ancestor of `origin/main`
via `git merge-base --is-ancestor`), and a live re-run of the ledger tooling against this
epic's own tree post-migration.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Per-concern ledger split (`status.json` header-only, `resume_anchor.md`, `queue/{PLAN-ID}.json` per row, generated `queue-view.md`) | shipped-as-specified | Live-verified on this epic's own tree: `migrate-layout` produced `resume_anchor.md`, `queue/PLAN-01.json`..`PLAN-11.json`, `queue-view.md`, and stripped the two GENERATED marker blocks from `epic.md`. `orchestrator --help` now lists `regenerate-view` alongside `queue`/`migrate-layout`/`compact`. |
| `status.json` no longer accepts `update-field --field plans` | shipped-as-specified | Matches the queue-write-boundary rule already in force; not independently re-tested (would require attempting the now-forbidden call). |
| `migrate-layout` command, converts old ledgers, refuses letter-suffixed rows | shipped-as-specified | Ran it live on `orchestrator-refactor`: `rows_migrated: 11`, `anchor_migrated: true`, `epic_blocks: [resume-summary removed, ordered-queue removed]`, `view_written: true`. The letter-suffix refusal (`unmigratable_rows`) is documented in the plan's own inbox finding (`-001`) but not independently reproduced here — no letter-suffixed row exists in this epic's own queue. |
| Cross-machine merge test (two machines' ledger edits merge cleanly) | shipped-as-specified | Reported 9/9 done in the plan's own facts; not independently re-run — accepted on the strength of `deliverables_done: 9` plus 27,761 passing tests at the recorded merge commit. |
| Row-status vocabulary prose reconciliation | shipped-as-specified, with a residual folded elsewhere | PR body states the schema itself landed earlier via #1539; this PR reconciles stale prose only. `review-apparatus/epic.md`'s own D2 prose was NOT edited directly — routed via inbox message per the Ledger Write-Boundary (confirmed: that epic already reconciled it in this session's earlier `land-all`, PR #1596). |

Realized footprint not independently re-derived (`surface_delta.state: unmeasured` —
neither declared nor realized paths were supplied to `landing-check`); accepted on the PR's
own stated file list (`_orchestrator_ledger.py`, `orchestrator.py`, `_orchestrator_inbox.py`,
~10 docs, tests) rather than re-verified against a diff.

## Metrics and Anomalies

- Tokens: 10,534,182 total, 70,372s (~19h32m) wall time.
- Anomalies: **Pre-submission self-review did not converge** — 4 rounds (10/2/6/6 findings,
  21 of 24 `contract_drift`); the operator closed it out of budget with the last 6 fixes
  (`b473f1f7a`) never self-reviewed. After the PR-review fix round (TASK-14..17), the
  operator chose "gates + push only" — `lessons-housekeeping`, `simplify`, `plugin-doctor`
  and `self-review` were **not** re-fired against those fixes (records stay anchored at
  `3a8bed617`); full `verify` (27,761 tests), CI, and CodeRabbit's second review **did**
  cover them and came back clean. `record_metrics.any_phase_missing_end_time: false`.

## Routing and Merge Behavior

- Review: CodeRabbit's second review came back clean after 6 findings from the first
  review were fixed. `automatic-review` and `branch-cleanup` both recorded `done`.
- CI/merge: merged via the merge queue at `21578e447`, confirmed as an ancestor of
  `origin/main`. `cleanup_owed: false`.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `#1609`
- [x] row `landing` stamped → `landings/PLAN-02.md`
- [x] row `plan_marshall_plan_id` stamped → `ledger-decomposition-and-row-vocabulary`
- [x] epic.md narrative reconciled (Decisions entries for the inbox drain; new Open Defect
      for the cross-epic `migrate-layout` sweep)
- [x] resume anchor updated
- [x] `queue-view.md` regenerated

## Follow-Ups

- **Cross-epic `migrate-layout` sweep (all 25 orchestrator epics)** — recorded as an Open
  Defect, operator decision needed (see epic.md); NOT actioned beyond this epic's own tree,
  which is outside this session's write-boundary.
- **`review-apparatus` D2 prose reconciliation** — already landed independently in this
  session's earlier `land-all` (PR #1596), before this landing was processed.
- **Transition-mailbox `not_orchestrated` misreport (lesson `2026-09-23-15-001`)** —
  recorded as a second Recurrence on the existing lesson (see Decisions).
- **8 candidate-lessons about other components** — 7 promoted to the global corpus
  (`2026-09-24-09-001,003,004,005,006,007,008`), 1 recorded as a recurrence on
  `2026-09-23-05-001` (BlockScalar/`reduced_transcript`).
- **`marshalld` daemon reconcile deferred** (daemon busy) — outside this epic's scope to
  perform; operator's own infra maintenance.
- **`/marshall-steward`** (marshal.json reported stale by the plan) — outside this epic's
  scope; a project-configuration action, not an orchestrator-ledger one.
- **Chore(quality-gate) commit carries an unrelated ruff import-order fix** to
  `test/test_shared_harness_parse_ns_{defaults,no_seam}.py`, attributed to main `#1593` —
  noted, not actioned; outside this epic's own surface.
