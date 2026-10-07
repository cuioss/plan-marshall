envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T21:55:30Z

component=plan-marshall:manage-execution-manifest
category=improvement
title=A plan cannot exercise a fix to its own finalize - the manifest was frozen at outline time

# A plan cannot exercise a fix to its own finalize - the manifest was frozen at outline time

## Observation

PLAN-CIS-028 reordered the finalize post-run-review steps to run **after** the merge gate. It could not exercise that fix: its **own execution manifest was composed at outline time with the old order**, so its own post-run-review steps — including the lessons-capture that produced this message — still ran *before* the merge gate.

The fix is correct and landed; it is simply **unobservable from inside the plan that shipped it**. The first evidence that it works comes from the next plan whose manifest is composed after the change lands.

## Why this recurs

The manifest is a **snapshot taken at outline time**. Any plan that changes finalize-step ordering, step selection, or step frontmatter is changing the thing its own snapshot already froze. This is structural, not an oversight — and it is the second recorded instance: PLAN-10 hit the same wall (a plan fixing a finalize-time component cannot have that fix exercised by its own finalize, because the cache syncs at step 19 and the retrospective runs at 17).

## Rule

- When a plan's deliverable modifies **phase-6 finalize step ordering, selection, or step frontmatter**, state explicitly in the outline that the change is **not self-exercising**, and name the observation point: the *next* plan composed after the merge.
- Do **not** accept the plan's own green finalize as evidence the ordering fix works. That green was produced by the pre-change manifest.
- The verification that actually counts is either (a) a derivation-level test over the composed manifest (which this plan did ship — the guard asserting no post-run-review step precedes the merge gate), or (b) an explicit post-merge observation on the following plan. Prefer (a); record (b) as owed residue when (a) cannot cover it.
- Generalizes beyond ordering: **any plan whose deliverable is consumed by the plan lifecycle at a phase the plan has already passed** is in this class — outline-time manifests, plugin-cache-synced skills, executor regeneration.

## Impact

`manage-execution-manifest` (snapshot-at-outline semantics), `phase-3-outline` (self-exercisability call-out), `phase-6-finalize`, and every future plan touching finalize step order or the plugin-cache/executor path.
