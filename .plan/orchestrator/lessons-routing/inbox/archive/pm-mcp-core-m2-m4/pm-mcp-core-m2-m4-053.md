envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:15Z

# Read re_review_on_loopback from the manifest step_params in the review leaf

## Context

In PLAN-06 the second automatic-review firing (HEAD 64414e3) found the required bot
cuioss-review-bot `participated_stale` and returned loop_back. The leaf stated that the stale-bot
remedy (a `/review` re-trigger) "is gated by `re_review_on_loopback`, which is `false` for this
plan", so it posted no trigger. The execution manifest of the same plan stamps
`phase_6.step_params.automatic-review.re_review_on_loopback: true` (with
`re_review_on_branch_cleanup: true`, `re_review_await_timeout_seconds: 600`). The operator first chose
"Post /review trigger", then merged over the stale review with barrier-ask-override.

## Root cause

The leaf resolved the flag from a source other than the manifest step_params the plan composed
(likely a marshal.json default or a different key), so the two disagree. Not yet verified which
source the leaf read.

## Proposed action

Check where automatic-review resolves `re_review_on_loopback` and make the manifest
`phase_6.step_params.automatic-review` value authoritative; log the resolved value and its source on
every firing so a disagreement is visible in the decision log.

## Evidence

- aspect: manifest_decisions - manifest step_params automatic-review re_review_on_loopback: true
- aspect: chat_history_analysis - automatic-review leaf at 64414e3: "re_review_on_loopback, which is false for this plan"
- status.json: automatic-review prior_firings done, loop_back(6-finalize), done; merge under barrier-ask-override

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-06-store-substrate-011.md` from plan plan-06-store-substrate (PLAN-06, #26)
