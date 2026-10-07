envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=landing
created=2026-08-27T19:00:00Z
revision=1
amended=2026-08-27T19:01:00Z

## What landed

`move-back-guard-resolves-through-its-own-tree` shipped as PR #1361 (merged) — all three failure-mode polarities of `cmd_worktree_remove`, closed together because two of them had been masking the third.

```landing-facts
schema=landing-facts/1
plan_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
pr=1361
merge_state=merged
deliverables_total=8
deliverables_done=8
total_tokens=14619534
total_wall_seconds=83037
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:skipped,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
merge_commit=5f972ac15
commits=19
files_changed=18
tasks_completed=16
work_units_shipped=17
loop_back_iterations=2
loop_back_ceiling=3
pending_findings_at_close=0
total_billing_weighted=130855281
```

## Residue

**H3 refuted by probe, and it strengthened the fix.** `git -C {wt} worktree remove {wt}` returns rc=0 and destroys the tree in 4/4 geometries — with and without `--force`, cwd inside and outside. There is no downstream backstop; the fail-open guard stood alone. Three documents asserted the opposite ("git refuses to operate on a worktree that is a shell's cwd"); all three instances were removed in one revision.

**The plan reproduced its own defect class five times, each caught by a different mechanism** — pre-submission self-review, an operator-facing premise error, an external reviewer, our own fix agent, and CI. Emitted as candidate-lesson 008 with the mechanism-to-shape mapping, stated as a floor over eight cited records rather than a partition.

**One population produced four answers across the run — 6, 7, 4, 8 — and three were published as fact before refutation.** Root cause: `architecture search --content`'s top-level `count` is a ROW count, double-counted across dual module attribution. Emitted as candidate-lesson 003.

**An external reviewer diagnosed a real methodological defect and reproduced its own class one rung up the ladder.** CodeRabbit correctly caught a population derived by literal text matching (it counted a comment as a call), then proposed an AST count that misses an aliased import — name matching at a higher rung is still name matching. Emitted as candidate-lesson 007.

**Seven defects handed forward, live in merged main, NOT fixed here** (global lessons, all with bodies):

- `2026-08-27-07-001` phase-5-execute — `scope_creep_check` is structurally inert on EVERY plan; `plan_creation_sha` has readers and tests but no writer. This plan had zero scope-creep coverage, and an undeclared file did escape, caught incidentally by `baseline-reconcile`.
- `2026-08-27-07-002` script-shared — the star-unpacked `load_script_module` idiom is a loader-guard blind spot that propagates by copying between sibling test files.
- `2026-08-27-09-001` manage-run-config — the display-timezone helper-only guard matches raw file TEXT, so a comment citing a helper name counts as reaching a timestamp. Carries a perverse incentive: the cheapest fix is deleting the true comment.
- `2026-08-27-12-001` manage-change-ledger — a leaf fabricated a commit SHA into the append-only ledger, reconstructing 40 chars from an abbreviated 9. The prefix matches, so a spot-check passes. Consumers must take the LAST row per `deliverable_id`, not the first.
- `2026-08-27-12-002` manage-tasks — `pre-commit-verify-freshness` cannot distinguish a compile from a full test run; every canonical shares the notation `pyproject_build`. A `fresh` verdict is NOT evidence that `module-tests` ran.
- `2026-08-27-14-001` tools-integration-ci — `ci pr create` declares a verb-scoped `--plan-id` while the router strips a `--plan-id` anywhere in the argv, making the documented preferred routing flag unusable on that verb.
- `2026-08-27-18-001` manage-findings — a review false positive filed as `accepted` makes `false_positives_count` read zero. Observed rate was 2 of 8 inline (25%) against a reported 0.

**Instrumentation gap.** Three independent ledgers reported `6-finalize` as having done nothing — `metrics.toon` carried only a `start_time`, no accumulator or dispatch-boundary file existed, and `execution.toon`'s `execution_log` held zero rows for the phase. The `enrich` pass closed the token half (6/6 phases, 14.6M tokens), but the per-step execution log for `6-finalize` remains empty because most finalize steps ran inline in the orchestrator rather than as dispatched agents. Emitted as candidate-lesson 002.

**Review coverage caveat.** This PR received NO Sourcery review at any HEAD — `refused_structural` at every push, cause `size`: cap 150,000 diff characters against a diff that grew to ~2,857 changed lines. Sourcery is optional so it never gated, but the gap is real and quantified. `pr-agent`, the only required bot, participated at two HEADs and found nothing both times; it is `issue_comment`-only, so it can never HEAD-bind through a check and needed an explicit `/review` trigger each time. CodeRabbit was the only bot producing actionable findings and hit its 1/hour ceiling twice.

**One shipped work unit has no task record** — an operator-approved orchestrator scope addition, after three pending-task TOON schema rejections. 16 recorded tasks against 17 real units. A stray `work/pending-tasks/default.toon` survives in the plan directory.
