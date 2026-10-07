envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=landing
created=2026-08-27T15:11:36Z

## What landed

PLAN-TRUTH-098 (WS-01) shipped as #1359 (merged) — the plan-footprint machinery is now resolvable and reconcilable by its own graders, and this run is the first on this repository whose retrospective resolved a post-merge footprint.

```landing-facts
schema=landing-facts/1
plan_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
pr=#1359
merge_state=merged
deliverables_total=7
deliverables_done=7
total_tokens=9203064
total_wall_seconds=85122
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:unknown,archive-plan:unknown
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=4
step.finalize-step-sync-baseline.work_performed=true
step.create-pr.pr_number=1359
step.branch-cleanup.action=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.work_performed=true
```

## Residue

**The remedy took, and the answering tier is named — but it is NOT the tier this plan added.**
The retrospective resolved a post-merge footprint (33 paths). The tier that answered was **tier 2,
`realized_capture`**, not the newly-added tier 4 (`pr_landing`): `branch-cleanup` wrote the realized
capture before removing the worktree, so tiers 2 and 3 both had material and the fall-through never
reached tier 4. D1's new tier is therefore **shipped and controlled-tested but unexercised in the wild
by this run**. Do not read this landing as the new tier validating itself. `references.merge_commit_sha`
is populated (`841f9093…`), which is exactly the condition under which tier 4 is not consulted.

**Tier 3 independently reproduces tier 2 exactly, but nothing in the pipeline performs that
cross-check.** `git diff --name-only 841f9093^1 841f9093` returns the same 33 paths, symmetric
difference 0. The retrospective agent did this by hand; no aspect or script does it. Mechanisable, not
mechanised.

**Arm 2 measured on this plan's own run — the matched-length trap fired.** `affected_files` carried 33
declared paths and the landing realized 33: **equal cardinality, non-identical membership**.
`collect-fragments.py` was recorded and never changed; `logging-gap-analysis.md` was changed and never
recorded. A count comparison reports perfect agreement over a set that disagrees — precisely what D4's
symmetric-difference verb exists to catch. Recall 97% (32/33) against the spec's 81.25% baseline;
`read_intent_excluded: 4` (references carries 4 read-intent files) shows D3 partitioning as designed.
D7's aspect 15 first run: 42 assessments vs 33 realized — `include_unrealised` 1/33,
`touched_but_unassessed` 1/33, `exclude_violated` 0/9. D6's aggregate did not fire (all four derived
roster members resolved) — its matched negative control passing.

**⛔ Two live defects shipped into main. Neither is fixed by #1359; both need epic follow-up.**

1. **Documented capture commands name a file no step creates.** The plan-retrospective reference docs
   `references/routing-decision-verification.md` (aspect 13) and the newly-shipped
   `references/outline-vs-shipped.md` (aspect 15) both instruct the capture into `work/footprint.txt`.
   Run verbatim, both aspects exit 1; they produced fragments in this run only because the
   retrospective agent deviated from the documented command. The new `outline-vs-shipped.md` copied
   its broken sibling's reference — a defect propagated by imitation into the very deliverable meant
   to close the gap.
2. **"Phase Dispatch Boundaries" is a permanently dead report section.** `compile-report.py` reads a
   top-level `dispatch_boundaries` key; `analyze-logs.py` nests it inside its log-analysis fragment;
   no aspect registers it. The omission classifies as benign (`sections_omitted`), so the loud half
   never fires. Test fixtures hand-construct the key, so the suite is green over a shape production
   never emits — a green suite proving a contract production does not satisfy.

**Producer gap: `record-metrics` recorded no typed facts.** Its `display_detail` carries the totals as
prose ("8h12m worked / 9.2M tokens / 185M billing-weighted") but its `phase_steps` record has no
`facts` sub-dict, so `total_tokens` / `total_wall_seconds` could not be read from where the landing
spec points. This landing read them from the metrics store instead (9,203,064 dispatched /
185,422,539 billing-weighted / 8h12m worked / 23h38m wall). The figures are true; the routing is not
yet mechanised. This is the payload spec's finding-#2 shape and is named here rather than degraded to
`unknown`. **Billing-weighted 185.4M is not carried as a required fact** — the schema has no key for
it, and phase 6 alone accounts for 4,996,549 dispatched / 96,178,416 billing (52% of the run's
billing).

**Two `steps` elements read `unknown` by construction.** `emit-landing` cannot observe its own terminal
outcome, and `archive-plan` (order 1100) has not run when the landing is written. Writing `done` there
would fabricate a state the run did not observe. Structural, not a producer defect — but it means
`steps` can never be complete for the last two composed slots.

**Review participation.** 4 bot-review rounds. **CodeRabbit (OPTIONAL) produced the entire actionable
yield**: 8 actionable, 7 fixed, 1 declined, 0 false positives. **pr-agent (REQUIRED) participated in
all 4 rounds with 0 actionable.** **Sourcery reviewed no version of this PR** — `refused_structural`,
size cap 150000 vs 6188 changed lines. The required bot contributed nothing and an optional bot
carried the gate; a size-capped reviewer silently reviewing nothing is the recurring
non-participation shape.

**⭐ Four separate fixes in this run each introduced a defect of the class they were fixing** (all
doc-contract). The convergent remedy in every case was **deletion plus a pointer to the authoritative
source**, never a corrected restatement. Five pre-submission self-review rounds found 8 real defects;
three plugin-doctor passes and the whole-tree gate found 0 — the structural gates did not see this
class at all. Phase 6 spent 3 loop-back iterations of a 5 ceiling.

**10 candidate-lessons already queued in this epic's inbox** (9 from `plan-retrospective`, 1 from
`lessons-capture`), messages 001–010 from this sender. Drain them alongside this landing.
