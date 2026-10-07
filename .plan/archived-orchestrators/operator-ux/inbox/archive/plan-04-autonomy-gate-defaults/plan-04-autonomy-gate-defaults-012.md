envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=landing
created=2026-09-07T12:49:20Z

## What landed

plan-04-autonomy-gate-defaults shipped as PR #1437 (merged via the platform merge queue at ef6aff8357733f18c6e629ad70c213302f906fcc).

```landing-facts
schema=landing-facts/1
plan_id=plan-04-autonomy-gate-defaults
epic=operator-ux
pr=1437
merge_state=merged
deliverables_total=4
deliverables_done=4
total_tokens=6689612
total_wall_seconds=71811
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.pre-submission-self-review.rounds=4
step.pre-submission-self-review.findings=11
step.automatic-review.coderabbit_reviews=2
step.automatic-review.findings=7
step.branch-cleanup.merge_route=merge_queue
```

## Residue

Items the epic should track that no step recorded as a fact.

**The two deliverables the spec named did not land where it said.** `final_merge_without_asking` has no default in `_config_defaults.py` — it is declared in `branch-cleanup.md`'s `configurable:` frontmatter and resolved through `configurable_contract.py`. The spec's deliverable 2 assumed the seed file. The flip is correct; only the location differed, and the PR body records this so a later reader does not go looking in the wrong file.

**Deliverable 3's keep/flip verdict column was moved out of user documentation.** Self-review finding `20608c` established that `keep`/`FLIP` tokens are transitional information, which the Documentation Standards forbid in permanent user docs, and that they read ambiguously as advice to the operator. The census column became `Halt behaviour` (current-state), and the 25 per-gate verdicts moved to the PR body, which is a dated record. Deliverable 3's substance is delivered; its artifact is not the one the spec named.

**An operator decision overrode the outline's recorded verdict.** The outline recorded *keep `false`* for `final_merge_without_asking` with three grounds (merging is outward-facing and irreversible; `plan_without_asking` is the planning-side checkpoint and this is the shipping-side one; the opt-in path already worked). The operator overrode it deliberately. The residual guards on the now-default auto path are `pre_merge_comment_barrier` and the cross-plan merge mutex, both recorded at the declaration site and in the PR body.

**CodeRabbit's CWE-862 finding was declined, not fixed.** It argued that auto-admitting a `5-execute` loop-back runs fix tasks the planning approval never authorized. Declined on three grounds (one principal with no external reachability; the bound it claimed missing exists as the pre-knob ceiling admission gate reading a persisted count; fix-task content is itself bounded), with the concession recorded that the consent point genuinely moved. Two prior verification passes had settled the same question against the implementing dispatcher. The epic may want to revisit this as a design question rather than a review comment.

**This project's `max_iterations` is 17, not the documented default 3.** The orchestrator read the documented default and propagated "the ceiling is spent" into three dispatches before the unified triage caught it. No decision reversed. Worth the epic's attention because the same defaults-vs-live-value confusion is what deliverable 4's parity test exists to prevent, and it recurred three times in this run — including a fabricated `head_at_completion` SHA the orchestrator self-caught and corrected.

**Two machinery defects were found by review leaves and are unfixed.** `automatic-review/SKILL.md` Branch A's `mark-step-done` snippet omits `--force`, so every terminal pass following a loop-back hits `error: conflict` (hit twice this run). `review_completeness.py check` rejects the invocation its own SKILL.md documents, because the template interpolates `--measured-diff-size` unconditionally while the flag takes a required value — failing on the common path where no bot refused for size.

**`references.modified_files` is a retired shim that can never succeed.** The lessons-housekeeping step's Step 3 names it as an input; it returned `field_not_found` on all three runs, and the step's documented fallback names the retrospective report, which does not exist at that order. Both documented inputs are simultaneously unavailable by construction.

**Finalize consumed 55% of the plan's tokens**, outspending 5-execute 2.8:1 across 17 dispatch boundaries, driven by head-dependent steps re-firing on every HEAD advance (`pre-push-quality-gate` ×6, `automatic-review` ×5, `plugin-doctor` ×4). None of those steps declares a `verdict_inputs` surface, so the verdict-currency classifier can never narrow a re-fire.
