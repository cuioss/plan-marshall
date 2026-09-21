envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=landing
created=2026-08-02T21:53:20Z

## What landed

**PLAN-CIS-028 — post-run review steps ordered before their evidence exists**

- PR: [#1080](https://github.com/cuioss/plan-marshall/pull/1080) — `fix(phase-6-finalize): reorder post-run-review steps after the merge gate`
- Branch: `feature/post-run-steps-ordered-before-their-evidence`
- Tasks: 22/22 done, 5 deliverables, track `complex`, scope `single_module`, 24 affected files.

### Shipped surface

1. **New `post_run_review` frontmatter fact** on finalize steps, plus a reorder that moves every post-run-review step *after* the merge gate, so a step that reads the landed state no longer runs before that state exists. `DEFAULT_PHASE_6_STEPS` migrated to the post-reorder order; a derivation guard asserts no post-run-review step precedes the merge gate.
2. **`head_dependent` declared** on the project-local finalize steps that resolve something from HEAD.
3. **Unresolvable footprint is now reported as *unmeasurable*, never as a confident zero** — and the retrospective instruments that failed in the confident direction were repaired (ordering-derived `inconclusive` vs `fail` distinction for `metrics_generated`; recall-fail split from inconclusive severity in artifact-consistency findings).
4. **`finalize-step-preference-emitter` gained an orchestration branch**, so it stops leaking into the global lessons store on orchestrated runs. The third lesson-emitting write site is now registered across standard, dispatcher and test.
5. **TASK-021 — runtime tracked-file check for post-run-review steps**, added because CodeRabbit rejected "document the gap honestly" as a fix for a `mutates_source: false` property that rested on a frontmatter declaration with nothing observing it.
6. **Built-in Step Dispatch Table derived from the manifest** instead of hand-maintained.

### Residue the epic should track

- **This plan could not exercise its own fix.** Its execution manifest was composed at outline time with the pre-reorder step order, so its own post-run-review steps (including this lessons-capture) still ran *before* the merge gate. The fix is only observable from the next plan composed after this lands. Same archetype as PLAN-10's finalize-ordering defect: a plan that fixes a finalize-time component cannot have that fix exercised by its own finalize.
- **Two review-apparatus concerns are handed over for cross-epic delegation** (see the two `candidate-lesson` messages flagged `Suggested routing: review-apparatus`): measured pr-agent/CodeRabbit value divergence on this diff, and CodeRabbit declining to re-review after a loop-back while the participation quorum still read green. Per the standing three-way routing rule these belong to `review-apparatus`, not to `code-intelligence-substrate`.
- **Post-merge PR revisit is owed on #1080** — the merge routinely outruns the review, and the final 8 commits of this PR carry no bot review at all.

### Signals observed at finalize

- Q-Gate findings resolved in 6-finalize alone: 19 (lower bound; not the full five-phase sum).
- Automated-review signal: 1 (actionable review-bot findings remediated in-run).
- Script-failure clusters: 0.
