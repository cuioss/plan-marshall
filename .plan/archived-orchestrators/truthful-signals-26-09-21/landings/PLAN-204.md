# Landing Analysis: PLAN-01 — Ledger joins and retrospective honesty

epic: quality-aspect
workstream: WS-01
pr: #1545 (https://github.com/cuioss/plan-marshall/pull/1545)

> Landing record for one shipped plan. Lives at `landings/PLAN-01.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated: PR #1545 `state: merged`, `merge_commit_sha afce081b…` == HEAD,
main clean, archive `2026-09-20-ledger-joins/` present. PR body Changes match the
redesigned 10-deliverable spec; inbox landing-facts report
deliverables_total=10, deliverables_done=10.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Step-id join key + union_rows | shipped-as-specified | PR body + `_ledger_reconciliation.py` in diff |
| Per-task changed_files persistence | shipped-as-specified | PR body + `_tasks_core.py`, `_cmd_step.py` in diff |
| [OUTCOME] on every done transition | shipped-as-specified | PR body + artifact-emission tests in diff |
| analyze-logs build_count reconciliation | shipped-as-specified | PR body + `analyze-logs.py` in diff |
| RE_ENTRY_COVERAGE decoupling | shipped-as-specified | PR body |
| Batched fragment registration | shipped-as-specified | PR body + `collect-fragments.py` in diff |
| Per-firing DISPATCH comparison | shipped-as-specified | PR body + `check-dispatch-audit.py` in diff |
| Manifest-consistency caveat | shipped-as-specified | PR body + `check-manifest-consistency.py` in diff |
| Split-plan footprint union | shipped-as-specified | PR body + `_footprint_resolver.py` in diff |
| Single-root fragment paths | shipped-as-specified | PR body |

## Metrics and Anomalies

- Tokens: unmeasured population (transcript-less opencode target, no usage envelopes) — recorded, not smoothed. total_tokens=0 in landing-facts reads as unmeasured, never as zero-cost.
- Duration: 68143s wall over 33 tasks (10 deliverables + 13 review-fix + 10 verification).
- Loop-backs: 3 iterations (self-review verifier procedure ×2, review-triage fixes ×1), all closed, bounds respected (3/14).
- Anomalies: push freshness refused twice (worktree_mutated, then build_scope_narrow) — settled via documented reconciliation, then covering whole-tree verify (27,136 tests green). Stale required reviewer blocked the barrier once; re-review trigger brought cuioss-review-bot current. compliant-paths dirtied main mid-run (surface match); reverted before merge.

## Routing and Merge Behavior

- Review: 14 bot comments, all triaged and fixed. Plugin-doctor caught 1 real violation (archived-mode example missing --plan-id); fixed, gate green.
- CI/merge: green on merged HEAD; platform merge queue, squash afce081b; branch pruned, worktree removed. No rebase conflicts with sibling work.
- Exemptions: light-lane 2-refine bare-transition refusal + pr_title capture block filed to process-compliance, both operator-approved with explicit exemptions.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-01 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-01 --field pr --value #1545`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-01 --field landing --value landings/PLAN-01.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-01 --field plan_marshall_plan_id --value ledger-joins`
- [x] epic.md queue reconciled from status.json
- [x] inbox drained: 007 reconciled (corroborates this report, 10/10 match); 001 folded→PLAN-10; 002 folded→PLAN-02 (+manage-metrics surface, same act); 003 folded→PLAN-17; 004 discarded (routine single-instance remediation, retained here); 005 folded→PLAN-12; 006 folded→PLAN-17
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

- PLAN-10: changed_files uniformity residual (finalize-step/late-dispatch closes, 31/33 measured) — folded from ledger-joins-001, no new surface.
- PLAN-02: dispatch-boundary rows for finalize-step terminations (45 execution vs 0 boundary rows) — folded from ledger-joins-002, manage-metrics surface added in the same act.
- PLAN-17: verifier-substitute evidence rule + CI deadline_exceeded as re-poll signal — folded from ledger-joins-003/006, no new surface.
- PLAN-12: argparse-rejection recurrence (8 notations, invented subcommands) — folded from ledger-joins-005, no new surface.
- Watch: transcript-less token totals unmeasured — known mechanism (gap flag), no new defect; re-check if a transcript-capable target ever reports the same.
