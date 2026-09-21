envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:18:40Z

component=plan-marshall:phase-6-finalize
category=improvement

# Finalize re-firing dominates plan cost at 53% of all tokens

## Context

This plan shipped a 4-file change (2 production files, 2 test files; 254 insertions, 24 deletions) and consumed 3,622,870 tokens. The `6-finalize` phase alone accounted for 1,937,959 of them — 53%, more than execute (679,658), outline (430,651) and plan (419,700) combined. The `(scope_estimate, change_type)` anchor for `multi_module + tech_debt` sets its error column at 2.5M tokens and 180 minutes; the plan crossed both (3.62M tokens, 239 minutes wall). The token total is additionally a FLOOR, because `6-finalize` was never closed and its figure is a `(boundary floor)` fold of 14 dispatch-boundary rows, so true spend is higher still.

## Root cause

The cost is not in the code change; it is in finalize re-firing. Six finalize steps carry `firing_count` of 2 or 3 — `project:finalize-step-lessons-housekeeping` (3), `pre-push-quality-gate` (3), `project:finalize-step-plugin-doctor` (3), `pre-submission-self-review` (3), `finalize-step-simplify` (2), `ci-verify` (2), `automatic-review` (2), `branch-cleanup` (2) — roughly 24 firings across steps that would nominally fire once each. Two loop-back rounds drove this (`loop_back_iteration=2`): one productive (`pre-submission-self-review` returned findings), one forced by the merge-queue stall (`branch-cleanup`). Each re-entry re-runs expensive dispatched steps — quality gate, plugin-doctor, self-review — whose inputs did not change between rounds.

## Proposed action

Investigate whether a loop-back must re-fire steps whose HEAD-anchored inputs are unchanged. Several of these steps already record `head_at_completion`, and on this plan the three costliest re-fired steps all recorded the *same* SHA (`56d5d442`) across their later firings — evidence that the work was repeated against an identical tree. A re-entry check that skips a step whose `head_at_completion` still equals the live HEAD would have avoided most of the duplication. Note that the merge-queue-driven `branch-cleanup` loop-back (see the companion candidate lesson on merge-queue enqueue) is the avoidable trigger for one of the two rounds.

## Evidence

- aspect: plan_efficiency — `[BUDGET]` error findings: `multi_module+tech_debt error at 2.5M tokens` (3.62M observed) and `error at 180 min` (239 min observed)
- aspect: plan_efficiency — `max_phase_token_share=0.53`, `dominant_phase=6-finalize=1937959`
- status.metadata.phase_steps.6-finalize — `firing_count` 3 on four steps, 2 on four more; `loop_back_iteration=2`
- status.metadata.phase_steps.6-finalize — `pre-push-quality-gate`, `project:finalize-step-plugin-doctor`, `pre-submission-self-review` all record `head_at_completion=56d5d442d479680d913cbde688188df6b7115fc0` after re-firing
