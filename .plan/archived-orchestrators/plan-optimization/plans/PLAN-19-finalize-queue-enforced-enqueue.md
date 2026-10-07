# PLAN-19: finalize-queue-enforced-enqueue

epic: plan-optimization
workstream: WS-09

> Staged plan spec. The finalize sibling of PLAN-18 (desired outcome D). Consumer/org-surfaced
> (cuioss). Orchestrator-verified against source 2026-07-19. Re-ground citations at outline.

## Objective

Make phase-6-finalize branch-cleanup merge correctly on a queue-enforced branch: with
`use_merge_queue=true`, ENQUEUE the PR (do not direct-merge), with NO head-branch deletion at merge
time and NO direct-merge/admin fallback — both of which a mandatory queue rejects (GH013). This is
what makes "finalize's PR merge succeeds on a queue-enforced branch" actually hold once PLAN-18 sets
`use_merge_queue=true`.

## Deliverables

### D — queue-enforced enqueue in branch-cleanup

**Verified:** `branch-cleanup.md` HAS `use_merge_queue` routing (`:358-380`, `:707` "Merge routing"),
but the merge call is `pr safe-merge --pr-number … --delete-branch` (`:543`) with a GitHub-only
`--admin` stuck-state DIRECT-MERGE fallback. On a mandatory-queue branch, BOTH `--delete-branch` and an
`--admin` direct merge are rejected (GH013). **Fix:** on `use_merge_queue=true`, enqueue via
`gh pr merge --auto` (through the CI abstraction) with **NO `--delete-branch`** and **NO direct-merge /
admin fallback**; head-branch deletion relies on the repo's `delete_branch_on_merge` setting.
**Outline MUST re-ground** how much of this the existing `:707` merge-routing already does vs. what the
`pr safe-merge` path still does wrong on a queue-enforced branch, and reconcile the admin stuck-state
fallback (PLAN-06's `admin_merge_on_stuck_state`) so it is NOT attempted on a mandatory-queue branch.
**Acceptance:** with `use_merge_queue=true` on a queue-enforced branch, finalize enqueues (no
`--delete-branch`, no direct-merge fallback) and the merge succeeds via the queue.

## Out of scope / do NOT expand
- Steward provisioning / bypass actors / external-queue detection — that is PLAN-18 (A/B/C).
- The `ci pr safe-merge` verb's non-queue (immediate) path — unchanged for `use_merge_queue=false`.

## Absorbs
- Desired outcome D from the cuioss merge-queue-coexistence spec.

## Expected Surface
- `phase-6-finalize/standards/branch-cleanup.md` (Merge routing, `use_merge_queue==true` path)
- possibly `tools-integration-ci` (`pr merge --auto` vs `pr safe-merge` on the queue path)
- tests: queue-enforced-branch enqueue (no --delete-branch, no fallback); non-queue path unchanged

## Dependencies and Sequencing
- Depends on: none hard (D is independent of A/B/C — it acts on `use_merge_queue=true` regardless of
  how it was set). Best VERIFIED end-to-end together with PLAN-18, but buildable separately.
- Overlaps with: in-flight PLAN-14 (both phase-6, different steps — quality-gate vs branch-cleanup) —
  rebase if both touch phase-6 SKILL/branch-cleanup. Disjoint from PLAN-18's surface.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-19-finalize-queue-enforced-enqueue.md"
```

## Status Trail
- plan_marshall_plan_id: finalize-queue-enforced-enqueue
- pr: #944 (MERGED 2026-07-19 via merge queue)
- landing: SHIPPED 2026-07-19 — re-grounding found desired-outcome D already implemented+tested at all three layers (doc/code/tests); residual was one documentation_only deliverable making the interactive Pre-Merge Confirmation Gate + auto-merge bypass authorization conditional on use_merge_queue (and matching the `(if <condition>)` template convention). Review loop (coderabbit f29119 + gemini 5ca57c) caught the auto-merge-bypass mirror site the plan missed → TASK-002/003. Verified end-to-end: finalize enqueued PR #944 via `pr merge-queue` on a genuinely queue-enforced main (no --delete-branch, no admin fallback), queue re-tested and merged. ⚠ owed: landings/PLAN-19.md via marshall-orchestrator.
