# Landing Analysis: PLAN-06 — Make finalize anchors unfabricable and the mutex reclaimable

epic: finalize-machinery
workstream: WS-04
pr: 1525 (https://github.com/cuioss/plan-marshall/pull/1525, merged as 1605831c5a8081f9b38b17d741fd910abb67717a)

> Landing record for one shipped plan. Lives at `landings/PLAN-06.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Corroborated against `ci pr view --pr-number 1525` (state merged, merge_commit
1605831c, PR body names all four lessons) and inbox landing message
plan-06-anchors-and-mutex-001 (`landing-check complete: false` — narrative-only, no
facts block; recorded as Open Defect, reconciled as far as it goes).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Unfabricable anchors (resolve, canonical hex, fail-closed refuse) | shipped-as-specified | mark-step-done rev-parse --verify, unknown_head_at_completion, leading---rejected; 6 new anchor tests; 8 legacy suites re-anchored to live SHAs |
| Reclaimable merge budget (stale-only eviction, FIFO dequeue, audit) | shipped-as-specified | merge_lock budget-reclaim verb; 6 new tests; wired into branch-cleanup budget path |
| Loud daemon (named serialization states, accurate escalation ERROR) | shipped-as-specified | routing resolutions + fallback-streak escalation suite |
| Sound handshake (drift key+counts, stderr mirror, PrTitleMissing) | shipped-as-specified | verify drift verdict key; extended handshake-findings suite |

22207 module tests green; quality-gate green; findings-check clean; CI 11/11 on rebased
HEAD. Step 2b verdicts: all 5 spec claims stamped `corroborated` via `corpus
set-verdict` (producer finalize-machinery/analyze, checked_at 1605831) BEFORE the
shipped transition — first landing in this epic to carry machine-persisted
re-grounding.

## Metrics and Anomalies

- Tokens/duration: no machine facts block (narrative landing) — wall time and token
  totals unrecorded; Open Defect notes a manual paste may surface them.
- Review: CodeRabbit 8 actionable → all fixed in 4714551 with "Addressed" markers;
  re-review stayed quota-blocked (4×90min waits + explicit command refused by bot
  policy); #1523 closed unmerged to re-trigger tooling on #1525.
- Incidents: upstream slice-040 cluster split landed mid-flight (remediation forwarded,
  suite green on combined tree); rebase + re-verify + force-push-with-lease;
  merge-queue conflict resolved the same way. Move-back waited ~6h on a live (fresh)
  slice-040 holder — never forced, correct. Archived
  (2026-09-18-plan-06-anchors-and-mutex), worktree removed, refs pruned, main clean.

## Routing and Merge Behavior

- Merge: squash via merge queue as 1605831c. cleanup_owed=false equivalent — no Watch needed.
- Process-rule observations went directly to the process-compliance inbox from the
  plan (no sanctioned-spec-read path, condensed phases 2–4, executor verb-registration
  second gate) — the routing rule working as designed; nothing to forward from here.

## Reconciliation Actions

- [x] 5 claim verdicts stamped corroborated — `corpus set-verdict` claims 0–4
- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-06 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-06 --field pr --value 1525`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-06 --field landing --value landings/PLAN-06.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-06 --field plan_marshall_plan_id --value plan-06-anchors-and-mutex`
- [x] epic.md queue reconciled from status.json
- [x] Open Defect opened: narrative-only landing (no facts block) on plan-06-anchors-and-mutex-001
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator compact` (in-place; invariants ok)

## Follow-Ups

- Inbox plan-06-anchors-and-mutex-001 (landing): reconciled (this report), archived on consume.
- The 4 epic-lesson copies for this plan's subjects (05-16-002/003/004, 03-16-005,
  19-006) stay corpus-retained until a housekeeping pass retires them against this
  landing — candidate for the next lessons sweep, not this drain.
- Refill emit per orchestrate.md selection (N=2, R=1 → 1 slot): see analyze output block.
