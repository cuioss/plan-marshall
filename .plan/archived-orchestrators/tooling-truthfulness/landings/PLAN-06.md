# Landing Analysis: PLAN-06 — Test falsifiability survey

epic: tooling-truthfulness
workstream: WS-05
pr: 1476 (https://github.com/cuioss/plan-marshall/pull/1476, merged as dc676c436b0c)

> Landing record for one shipped plan. Claims verified against ground truth
> (PR state via CI abstraction, HEAD, merge stat, landed files, worktree list,
> working tree) — the paste was a lead, never a fact.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — survey every `inspect.getsource` use and classify | shipped-as-specified | `test/plan-marshall/workflow-permission-web/inspect-getsource-classifications.md` at HEAD classifies 9 sites (keep 6, replace 3); population re-derived per spec instruction (spec said 8 files as a lead — survey found 9 sites, no manufactured count) |
| D2 — replace confirmed vacuous pins with behavioural tests | shipped-as-specified | Merge stat exactly 4 plan files: `test_gate_derivation_diagnosability.py` (AST structural assertion + matched control), `test_permission_ops.py` (rendered `--help` assertion + matched control), `test_permission_web.py` (live CLI no-settings-file test); 2 review-driven fix commits included; red-first per paste |

Corroboration: PR state `merged`, `merge_commit_sha dc676c436b…` == main HEAD (`git log`);
`git status` clean on main; PLAN-06 worktree removed (`git worktree list` shows main +
PLAN-05 worktree + one sibling-epic worktree + unrelated detached session). No drops,
no unplanned additions. Review mechanics (CodeRabbit mandatory finding fixed in 2356d28
with negative control, quota-refusal recovery via close-and-reopen as #1476) corroborated
via PR body/reviews as far as the read-side abstraction reaches; taken as paste-supported.

## Metrics and Anomalies

- Tokens: 0 (unmeasured on the OpenCode lane — recorded as absent, not as zero)
- Duration: `total_wall_seconds=48723.0` (~13h32m) per landing-facts, incl. ~7h stalled-envelope gap + bot quota waits
- Steps: 23/23 finalize done, 2 review loop-backs settled through CI, pre-merge barrier clean
- Residue: create-pr opened #1474 first; refusal-recovery re-delivered as #1476 (drain on #1476 — step fact still reading 1474 is imprecise, recorded not defected); `emit-landing:n/a, archive-plan:n/a` while both observably happened — same imprecision class as PLAN-03, landing-check reports `complete: true`

## Routing and Merge Behavior

- Review: CodeRabbit full review (1 actionable — startswith receiver pin), fixed with negative control, thread resolved, bot confirmed; sourcery approved; quota refusals recovered per fallback policy without 90-minute waits
- CI/merge: queue-merged; no rebase conflicts and no re-verify signals against concurrently-running PLAN-05 at ship time (disjoint surfaces held — no collision to record)

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-06 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-06 --field pr --value 1476`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-06 --field landing --value landings/PLAN-06.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-06 --field plan_marshall_plan_id --value implement-plan-06-test-falsifiability-survey`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] inbox drained: 3 messages (1 landing reconciled, 1 candidate-lesson promoted,
  1 folded as recurrence into corpus `2026-09-06-07-003`), all archived

## Follow-Ups

- PLAN-06's `corpus_spec` rows remain true of the declaration but no longer gate concurrency —
  landed plans leave the live set
- The survey's verify-first hand-off clause (broad class → sibling `test-quality` epic): the
  survey kept 6 / replaced 3 with no broad-class hand-off reported — nothing to route
