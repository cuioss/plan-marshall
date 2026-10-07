# Landing Analysis: PLAN-04 — Make branch verbs correct after cleanup deletes

epic: finalize-machinery
workstream: WS-03
pr: 1509 (https://github.com/cuioss/plan-marshall/pull/1509, merged as f8b0fa408293d78adb1bd5a68e2579ce3c6e9544)

> Landing record for one shipped plan. Lives at `landings/PLAN-04.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Corroborated against `ci pr view --pr-number 1509` (state merged, merge_commit
f8b0fa40, footprint_base_sha agrees) and inbox landing message
git-branch-mechanics-004 (`landing-check complete: true`, deliverables 2/2).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| branch-sync-state reaches remote_absent_landed after removal | shipped-as-specified | git-workflow.py main-checkout fallback probe; merged-and-deleted → push skip; new test_branch_sync_state_post_removal.py |
| prune tolerates deleted local branch, still prunes remote ref | shipped-as-specified | _cmd_prune_ref.py tolerated delete (warning, rc 1 only); new test_prune_ref_deleted_local.py; test_cmd_prune_ref.py updated with genuine-failure case retained |
| Branch-cleanup contract updated | shipped-as-specified | branch-cleanup.md + branch-cleanup-rereview.md ordering (move-back → removal → deletion, post-removal probes) |

All 4 declared source files touched; realized adds only test adjuncts. 8/8 tasks done,
6/6 phases closed. No refutation of any staged-spec HYPOTHESIS — no set-verdict writes owed.

## Metrics and Anomalies

- Tokens: 0 floor (OpenCode exposes no usage capture — known gap); wall 38313s
  (~10h38m). Steps: 21 done, 1 pending (archive-plan — normal pre-archive state),
  1 skipped (lessons-capture), 0 failed.
- Review: 8 actionable CodeRabbit comments across 3 rounds → TASK-4..8, all fixed
  and green; 1 suggestion declined with rationale; final triage clean, CI green on
  landed HEAD, participation complete.
- Waivers on record: no session identity (telemetry-only, absent on runtime —
  same class as PLAN-07 subject); self-review closed after two identical
  accepted-clean rounds on a deterministic surface (verifier twice held close on
  incurable grounds).
- Incident: main-checkout executor went stale post-merge (embedded pre-fix
  scripts); first post-merge prune ran the old abort path; regenerated via
  generate_executor, retry took the tolerated path. Forwarded to process-compliance
  inbox (P3 template-staleness recurrence evidence).
- Lesson 2026-09-04-14-005 retired as completely covered: orchestrator corroboration
  is `manage-lessons get` → not_found (absent from store), consistent with removal;
  clause+input evidence rides the plan's tombstone record.

## Routing and Merge Behavior

- Merge: direct merge as f8b0fa40 per paste (merge queue claimed by sibling runs;
  no conflict reported). Remote branch cleaned, plan archived to
  `.plan/local/archived-plans/2026-09-17-git-branch-mechanics`, main tree clean.
  cleanup_owed=false — no Watch needed.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-04 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-04 --field pr --value 1509`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-04 --field landing --value landings/PLAN-04.md`
- [x] row `plan_marshall_plan_id` already `git-branch-mechanics` (stamped at launch linkage)
- [x] epic.md queue reconciled; PLAN-04 worktree-residue Watch retired (clean move-back: branch cleaned, plan archived, main clean)
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator compact` (in-place; invariants ok)

## Follow-Ups

- Inbox git-branch-mechanics-004 (landing): reconciled (this report).
- Inbox git-branch-mechanics-003 (candidate-lesson, review_completeness flags):
  discarded — argparse/flag-shape family already corpus-held (19-004, 17-008,
  11-19-001, 13-12-005); not a structural process guard, so not forwarded.
- Stale-executor incident: forwarded to process-compliance inbox as orchestrator
  finding (second live instance of the P3 class).
- Refill emit per orchestrate.md selection (N=2, R=0 → 2 slots): see analyze output block.
