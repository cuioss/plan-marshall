envelope_version=1
sender_type=plan
sender_id=retrospective-completeness-and-phase5-marker
epic=test-suite-quality
kind=candidate-lesson
created=2026-07-28T17:04:53Z

component=plan-marshall:phase-6-finalize
category=bug
proposed_bundle=plan-marshall
origin_plan=retrospective-completeness-and-phase5-marker
origin_pr=1036

# The retrospective step is ordered after the steps that destroy its inputs and before the step that would make its own fixes live

`plan-marshall:plan-retrospective` sits at position **17** of this plan's 22 finalize steps.
Two steps that determine whether it can measure anything sit on the wrong side of it:

```
16  branch-cleanup                          <- removes the worktree (and the branch)
17  plan-marshall:plan-retrospective        <- runs HERE
18  project:finalize-step-deploy-target
19  project:finalize-step-sync-plugin-cache <- makes THIS plan's code live
```

This is one root cause with two independently-damaging symptoms. Both are observed in this
run, not hypothesised.

## Symptom A — it runs BEFORE the cache sync, so it executes pre-fix code

The executor resolves scripts through the plugin cache. At retrospective time the cache was
at `0.1.1240`, which predates merge `a8cc8ac`. This plan's D1 deliverable registered two
`SECTION_SPEC` rows; the retrospective that is supposed to exercise them ran against the
copy that lacks them:

```
$ collect-fragments add --aspect direct-gh-glab-usage
status: error
error: "Unregistered aspect key: 'direct-gh-glab-usage' … Valid aspect keys: [ …15 keys… ]"
```

Identical rejection for `execution-context-dispatch-audit`. Both fragments were produced and
both were thrown away. Verified as a **staleness artefact, not a regression**: merged main
carries both rows at `marketplace/…/plan-retrospective/scripts/retro_sections.py:50` and
`:54`; the cache copy's `SECTION_SPEC` ends at `permission-prompt-analysis`.

The general form is worse than the D1 instance: **a plan that fixes any finalize-time
component can never have that fix exercised by its own finalize run.** The same run shows it
for D3 — 16 steps recorded `outcome=done` in `phase_steps` against **7** `[STEP] Completed
step:` lines in `work.log`, a 9/16 (56%) miss rate, i.e. exactly the pre-fix behaviour D3
closed. Every one of this plan's four headline claims therefore rests on unit tests alone,
while the finalize pipeline reports green.

## Symptom B — it runs AFTER worktree teardown, so coverage measures against nothing

`check-artifact-consistency` derives the realized footprint live from the plan's worktree.
`branch-cleanup` removed it one step earlier. Result:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 10   found: 0   recall_pct: 0.0
```

The 10 declared files **were** all modified — they are the merge commit's exact diffstat.
The measurement is not wrong about the plan; it is wrong about itself. `direct-gh-glab-usage`
likewise returned `total: 0` with `status: success` on a diff surface that no longer exists.

**A missing input reported as a zero score is a false negative wearing a number.** `0%
recall` and `0 findings` are indistinguishable, to every downstream reader, from "measured
and clean". This is the epic's own theme — a confident signal hiding a caveat — inside the
instrument built to detect it.

## Corrective rule

**Two parts; the second is required even if the first is adopted.**

1. **Order the retrospective before the steps that invalidate its inputs and after the step
   that makes the plan's own code live.** Concretely: after
   `project:finalize-step-sync-plugin-cache`, before `branch-cleanup`. If those two
   constraints cannot both be met (cache sync legitimately wants a landed merge), then the
   retrospective needs an explicit re-resolution of its own script paths against the merged
   source rather than the cache.

2. **A coverage aspect whose input is absent MUST report `unavailable`, never `0`.** The
   footprint source is a precondition: when the worktree is gone and no fallback footprint is
   supplied, `check-artifact-consistency` must emit a skip token (the shape
   `chat-history-analysis` already uses — `status: skipped` + a named skip reason) instead of
   a 0% recall failure. Same for `direct-gh-glab-usage`'s diff surface. The distinction
   between "clean" and "not measured" must survive into the report.

## Impact

Every plan that runs the opt-in retrospective — so the measurement floor of this entire epic.
Symptom A additionally means **no plan can self-verify a finalize-pipeline fix**, which is
precisely the class of work `test-suite-quality` keeps producing. Symptom B silently
understates coverage on every plan, and the understatement is largest for plans that changed
the most files.

## Verification note

Both symptoms are reproducible from artefacts alone: compare
`status.metadata.phase_steps["6-finalize"]` key count against `grep -c 'Completed step:'` on
`logs/work.log`, and compare `references.affected_files` against the merge commit diffstat.
Neither requires the session transcript.
