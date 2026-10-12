envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:54Z

# Candidate lesson: A required review bot without a push trigger makes automatic-review loop back with no way to progress

- Component: plan-marshall:automatic-review
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-013 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during the finalize phase of plan primitive-spi-and-validators (PR #18). Checked against the decision log of the plan.

## What happened

`cuioss-review-bot` was a required bot. It has no push trigger and reviewed only the first commit of PR #18. After each fix push the automatic-review step found it `participated_stale` and recorded `loop_back`. It did so twice. Nothing the run could do would make the bot review the new head, so the loop could not end by itself. It ended when the operator moved the bot from `required_bots` to `optional_bots` for this plan only (plan-local step parameters; `marshal.json` untouched).

## Verification of the wording

- Confirmed: two `loop_back` outcomes of automatic-review (decision log 269436 at 23:44:18Z, 85984a at 00:15:49Z).
- Confirmed: `participated_stale` at 3144ca4, loop-back iteration 1/3 (f4ac48).
- Confirmed: operator decision of 2026-10-10 and its scope (762ee6), and the settled state "cuioss-review-bot optional and stale by operator decision" (318de9).
- NOT confirmed from the decision log: the setting `re_review_on_loopback false`. The log does not name it.

## Proposed rule

A bot may be listed as required only when it reviews again on push, or when the step can ask it to. For a required bot that reviewed an older commit and cannot be re-triggered, the step reports that state once and asks the operator, instead of spending loop-back iterations on a condition that cannot change.

## Evidence

- Decision log 269436, f4ac48, 85984a, 762ee6, 318de9.


## Recurrence: plan workspace-confinement (PLAN-03 of epic pm-mcp-core-m2-m4), inbox message workspace-confinement-012.md

**Candidate: a required review bot that reviews only on request went stale after every fix commit and blocked the review step**

Source: run observation backing the review signal, not a finding record of its own. Verified against the logs.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

## Evidence

- Work log `610d05` (2026-10-09T23:53:27Z): "2 new pr-comment findings filed; cuioss-review-bot participated_stale at head 252b4b1, recorded loop_back".
- Decision log `217eb0`: the review step was recorded with outcome `loop_back`.
- Decision log `572828` (2026-10-10T06:16:10Z, WARNING): "cuioss-review-bot moved from required_bots to optional_bots for this plan only (plan-local step-params; marshal.json unchanged) — its review is stale at the new head and re_review_on_loopback=false blocks the re-trigger".
- Work log `4650b6` (07:13:34Z): the pre-merge review check passed with "required-bot participation complete" only after that change.

## What happened

`cuioss-review-bot` is configured as a required reviewer and reviews only when it is asked to. With `re_review_on_loopback=false` the run does not ask again after a fix commit. The first fix commit (`252b4b1`, TASK-7) therefore left its review stale, the review step could not complete, and the run waited from 23:53Z to 06:16Z until the operator made the bot optional for this plan. `marshal.json` still lists the bot as required.

## Why it may be a lesson

The two settings contradict each other for any plan that needs at least one fix commit after review: required participation at the current head, and no re-request after a fix. The next plan of this repository meets the same block unless the project configuration changes.

Classification is left to the pickup.

## Recurrence

Recurred in workspace-confinement (#19) and lock-manager-and-leases (#20, inbox `lock-manager-and-leases-005.md`): automatic-review looped back at ab766d8 until the operator moved the bot to optional_bots. Three plans in a row. PLAN-38 of epic pm-mcp-core-m2-m4 sets `re_review_on_loopback` to true.
