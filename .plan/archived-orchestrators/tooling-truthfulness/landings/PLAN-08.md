# Landing Analysis: PLAN-08 — Slug semantics + model compliance

epic: tooling-truthfulness
workstream: WS-02
pr: 1487 (https://github.com/cuioss/plan-marshall/pull/1487, merged as 19143cbe6c1d)

> Landing record for one shipped plan. Claims verified against ground truth
> (PR state via CI abstraction, HEAD, merge stat, merged code, worktree list,
> working tree, archived plan logs) — the paste was a lead, never a fact.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — slug semantic at decompose Step 5 | shipped-as-specified | PR body + stat (`workflow/decompose.md`, 8 lines); merge stat file list matches |
| D2 — duplicate-slug lint on queue-write path | shipped-as-specified | `orchestrator.py:912` refusal arms (`duplicate_slug`, `epic_slug`), `invalid_field` reuse at `:1106`, checks at `:1140-1158`; red-first tests in `test_orchestrator.py` (+63) |
| D3 — shared-slug detector in resume-summary | shipped-as-specified | `_shared_slug_rows` at `:1430`, `_epic_slug_rows` at `:1624`, payload keys at `:1721-1726`; red-first tests in `test_resume_summary_self_validation.py` (+81) |
| D4 — bypass-enforcement registry (mechanism, no prose) | shipped-as-specified | `test_bypass_instrumentation.py` (+258): in-epic red-first gates + out-of-epic testable proposals with owners; spec's no-prose-rule bar honoured |

Corroboration: PR state `merged`, `merge_commit_sha 19143cbe6c…` == main HEAD (`git log`);
`git status` clean on main; PLAN-08 worktree removed (`git worktree list` shows main +
model-provisioning + sibling-epic worktrees + unrelated detached session). Merge stat
exactly the 5 plan files (670 insertions). Landing-check `complete: true` (+ live
`surface_delta` block, unmeasured). No drops, no unplanned additions.

## Metrics and Anomalies

- Tokens: 0 (no usage envelopes forwarded — recorded as honest floor per paste, not a total)
- Duration: `total_wall_seconds=45461.0` (~12h38m) per landing-facts
- Review: CodeRabbit 3 Major + 1 Major + 2 Minor across three rounds, all fixed over
  899473d/2942c7a/96becc1e (4/4 threads resolved, final Low); CI green every landed HEAD;
  rate-limit waits 4 of 10 used, 5th cut short per operator instruction
- Merge under barrier-ask-override (review-barrier-gap at 96becc1e: quota refusal, 0 pending
  findings, CI success) — second use of the override in this epic, same shape as PLAN-01
- Transcript enrichment skipped (SessionStart hook not installed) — same OpenCode-lane
  degradation as prior landings, wall time only

## Routing and Merge Behavior

- CI/merge: squash via queue; no rebase conflicts reported; no concurrent-plan collision
  (nothing else of this epic in flight — PLAN-08 ran alone)

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-08 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-08 --field pr --value 1487`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-08 --field landing --value landings/PLAN-08.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-08 --field plan_marshall_plan_id --value implement-plan-08-slug-semantics-model-compliance`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] inbox drained: 5 messages (1 landing reconciled, 4 candidate-lessons folded as
  recurrence with zero new lessons), all archived

## Follow-Ups

- Queue is now EMPTY (all 8 plans shipped) — this analyze is followed by `close`
- Folded-log triage (inbox -002, performed at drain): the 172 lines are routine retry/
  `--help`-probe noise plus already-known in-run recoveries (argparse drifts now in
  `2026-09-11-19-001`; session_id abort overridden per precedent; stale-push recovered via
  covering build). No new defect. Notable single: `collect-fragments add` internal error on
  a doubled plan-dir-relative path (caller-side, recovered immediately) — one data point,
  no pattern; recorded, not filed.
