envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=landing
created=2026-09-04T17:15:04Z

## What landed

every-module-counts-and-the-campaign-can-finish shipped as #1407 (merged).

```landing-facts
schema=landing-facts/1
plan_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
pr=#1407
merge_state=merged
deliverables_total=8
deliverables_done=7
total_tokens=4675938
total_wall_seconds=135219
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
```

## Residue

**Deliverable 5 is partial.** Two declared paths — `test_footprint_resolver.py` and
`test_footprint_tier_precedence_control.py` — were never touched, and nothing in the run records
whether the survey judged them non-removable. The remaining seven deliverables are complete, and all
five leftovers named in the objective were closed.

**No reviewer reviewed this diff.** The PR reached 515 files and both size-capped bots refused:
Sourcery on the GitHub API's 300-file diff-fetch ceiling, CodeRabbit on its 100-file plan limit.
`cuioss-review-bot` was triggered with `/review` and never answered. The operator accepted the
coverage gap under a `barrier-ask-override` merge authorization (granted twice — the first lapsed
when a rebase moved HEAD). Machine verification stands: whole-tree verify green at 24,246 tests, CI
green, and the merge queue re-verified against the latest base before landing. Neither refusal was
recognised at FIND time — Sourcery was credited as `participated` and CodeRabbit recorded `absent` —
until commit 394e0fcf registered both wordings as `cause=size` refusals.

**The scope growth and the lost review coverage are causally linked.** Deliverables 7 and 8 are
sweeps that declared an outline-time snapshot; execution reached roughly 300 more files, which is
what produced the 515-file diff the bots then refused. The outline carries no predicate-shaped
declaration form, so an honest sweep declaration is currently impossible to write. This is the
epic's to decide, not this plan's.

**Finalize cost was dominated by gate re-fires.** 6-finalize spent 2.40M tokens against 5-execute's
0.72M, driven by roughly 20 re-fires across five head-dependent steps. Every re-fire traces to the
verdict-currency classifier returning `invalidated` because none of those steps declares a
`verdict_inputs` surface, so any HEAD advance invalidates every recorded verdict. Two rebases onto a
moving `origin/main` multiplied it.

**A structural ordering gap in the finalize band.** `finalize-step-simplify` (order 8) commits after
`pre-push-quality-gate` (order 5) has certified its tree, so the gate/review delta was `excluded`
with `gate_head_sha != reviewed_head_sha`. The review-retrospective reports `structural_share: null`
rather than `0` as a result.

**`check-manifest-consistency` emits a false `fail` on any plan with branch-cleanup.** It reported
`branch_cleanup_without_changes` with `diff.files_total: 0` against a 521-path footprint, because
branch-cleanup is manifest step 13 while the retrospective is step 17 — the PR has merged by then and
`--base-ref origin/main` is legitimately empty. The SKILL's canonical block prescribes `--base-ref`
with no post-merge caveat.

**15 candidate-lessons were routed to this epic's inbox** (7 from `plan-retrospective`, 8 from
`lessons-capture`, messages 008-015). Candidates 010 and 011 name existing local lesson ids so the
epic can dedup rather than double-count.

**One lesson could not be retired.** `2026-09-03-17-001` is fully covered by this plan's codified
rule in `pytest-testing/standards/testing-pytest.md`, but `manage-lessons remove` returns
`not_found`: the lesson file opens with YAML frontmatter, so it is listable but unaddressable by
every id-keyed verb. Twelve lessons in the corpus share that shape. This is the open defect recorded
as `2026-09-03-22-001`; the file was deliberately not hand-deleted, which would retire it with no
tombstone.
