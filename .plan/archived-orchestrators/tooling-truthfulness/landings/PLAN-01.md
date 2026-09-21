# Landing Analysis: PLAN-01 — Script-surface validation

epic: tooling-truthfulness
workstream: WS-02
pr: 1466 (https://github.com/cuioss/plan-marshall/pull/1466, merged as 53ab7dd2e)

> Landing record for one shipped plan. Claims verified against ground truth
> (PR state via CI abstraction, HEAD, worktree list, working tree, merged
> code) — the paste was a lead, never a fact.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. Status-vocabulary validation gate + claim-index parser fix | shipped-as-specified | `orchestrator.py:164` defines `VALID_STATUS_VOCABULARY = frozenset({'staged','launched','running','parked','shipped','landed'})` with gate at `:1144`; PR #1466 diff adds gate + `_parse_claim_section` operational-bullet exclusion; `SKILL.md` publishes vocabulary under machine-locatable heading |
| 2. Cross-cutting regression tests | shipped-as-specified | `test_orchestrator_status_regression.py` (new), `test_orchestrator_claim_section_integrity.py` updated + interleaved-bullet ordinal case, `test_orchestrator.py` set-equality test; module-tests green per paste, quality-gate green |

Corroboration: PR state `merged`, `merge_commit_sha 53ab7dd2e…` == main HEAD (`git log`); `git worktree list` shows plan-01 worktree removed; `git status` clean on main; `VALID_STATUS_VOCABULARY` present at HEAD. Deliverable set 2/2, no drops, no unplanned additions.

## Metrics and Anomalies

- Tokens: 0 (untracked for this run) — same figure in paste and landing-facts; no conclusion drawn from it
- Duration: 11h57m wall (landing-facts `total_wall_seconds=43058.0`)
- Anomalies: 2 loop-back iterations (of 5 allowed) — iteration 1 triaged review findings into fix TASK-5, iteration 2 triaged 2 late barrier findings; Phase Breakdown supplement absent (renderer failed open per spec, noted not hidden)

## Routing and Merge Behavior

- Review: CodeRabbit 13 findings, all handled; declined re-review of fix HEAD twice (incremental-review decline); cuioss-review-bot stale by design (no push auto-review in this repo) — merged under operator-recorded `barrier-ask-override` via the merge queue, squash `53ab7dd`
- CI/merge: ci-verify all green; 1 upstream commit rebased over at sync-baseline; no rebase conflicts and no re-verify signals against concurrently-running PLAN-02 (disjoint surfaces held — no collision to record)
- Residue (from inbox landing message): merge-gap mechanics at `f89b2e41` documented there; no action owed

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-01 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-01 --field pr --value 1466`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-01 --field landing --value landings/PLAN-01.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-01 --field plan_marshall_plan_id --value plan-01-script-surface-validation`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] inbox drained: 6 messages (1 landing reconciled, 2 candidate-lessons promoted, 3 discarded with rationale), all archived

## Follow-Ups

- PLAN-04/PLAN-05 sequencing constraint lifts: both were held behind PLAN-01's landing analysis ("never concurrent") — eligible for pairing once analyzed; their `corpus_spec` overlap rows against PLAN-01 remain true of the declaration but no longer gate concurrency (landed plans leave the live set)
- Ledger now enforces `VALID_STATUS_VOCABULARY` on `queue --transition/--add-row --status` — future reconciliations that typo a status fail loud instead of persisting
- Inbox discrepancy noted, not defected: paste claimed "3 inbox message(s)" for lessons-capture but 5 candidate-lesson messages drained (2 retrospective + 3 capture); all 6 enumerated messages consumed, closure equation holds
