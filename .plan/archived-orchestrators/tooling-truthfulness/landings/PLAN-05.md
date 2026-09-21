# Landing Analysis: PLAN-05 — Declaration currency

epic: tooling-truthfulness
workstream: WS-01
pr: 1482 (https://github.com/cuioss/plan-marshall/pull/1482, merged as 3a79a9a6af13)

> Landing record for one shipped plan. Claims verified against ground truth
> (PR state via CI abstraction, HEAD, merge stat, merged code, worktree list,
> working tree) — the paste was a lead, never a fact.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — landed footprint reconciled against OTHER staged specs (read surface) | shipped-as-specified | `orchestrator.py:365` declaration-currency section, `corpus-declaration-currency` op at `:2093`, registered at `:4052`; symmetric difference both directions, `/`-boundary containment, distinct `unevaluated` state, `origin/main` base anchor with stale-local flagging; red-first guards in `test_orchestrator_corpus.py` with matched untouched-spec control |
| D2 — in-flight expansion as first-class `surface_delta` drain field (mechanism, no prose rule) | shipped-as-specified | `_orchestrator_inbox.py:1177` `compute_surface_delta`, reported at `:2299` with `added`/`missing`, `expansion_detected`, `vacuous`/`unmeasured` states; red-first guards in `test_landing_completeness.py` incl. read-only byte-identical-tree proof; spec's verify-first clause honoured — no fourth prose rule shipped |

Corroboration: PR state `merged`, `merge_commit_sha 3a79a9a6a…` == main HEAD (`git log`);
`git status` clean on main; PLAN-05 worktree removed (`git worktree list` shows main +
PLAN-07 worktree + one sibling-epic worktree + unrelated detached session). D2's mechanism
is live-proven: this very drain's `landing-check` returned a `surface_delta` block
(`unmeasured`, base `origin/main` @ `3a79a9a6a`, not stale). Superseded PR #1478 (closed
unmerged in rate-limit recovery) correctly excluded — drain on #1482. No drops, no unplanned
additions.

## Metrics and Anomalies

- Tokens: 0 (no session transcript — recorded as absent, not as zero)
- Duration: `total_wall_seconds=67052.0` (~18h37m) per landing-facts
- Steps: 4 tasks, 23/23 finalize steps (resumed envelope: prior run to ci-verify on #1478,
  resumed through review, queue-merge, post-merge, metrics, emit-landing, archive-plan)
- `archive-plan:pending` in landing-facts while archive observably completed (archived plan
  exists) — same step-fact timing imprecision as PLAN-03/06, recorded not defected
- Landing-check `complete: true` (plus a new `cleanup_owed` key the checker accepts)

## Routing and Merge Behavior

- Review: per paste, CodeRabbit mandatory review + findings triage through automatic-review;
  taken as paste-supported (PR merged via queue)
- CI/merge: queue-merged as `3a79a9a6`; no rebase conflicts and no re-verify signals against
  concurrently-running PLAN-07 at ship time (docs vs orchestrator surfaces — disjoint by
  construction, no collision to record)

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-05 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-05 --field pr --value 1482`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-05 --field landing --value landings/PLAN-05.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-05 --field plan_marshall_plan_id --value implement-plan-05-declaration-currency`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] inbox drained: 8 messages (1 landing reconciled, 3 candidate-lessons promoted,
  2 folded as recurrence, 2 discarded as shipped-with-tests), all archived

## Follow-Ups

- PLAN-05's `corpus_spec` rows remain true of the declaration but no longer gate concurrency —
  landed plans leave the live set
- The new `corpus declaration-currency` verb and `surface_delta` field change what future
  cross-check and landing-check reads report — subsequent emits and drains consume them directly
