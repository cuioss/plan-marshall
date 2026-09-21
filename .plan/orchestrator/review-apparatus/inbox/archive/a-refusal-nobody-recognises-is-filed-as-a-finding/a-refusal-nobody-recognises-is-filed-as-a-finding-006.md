envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:23:05Z

component=plan-marshall:phase-6-finalize
category=bug
title=The finalize dispatcher does not forward orchestrated/epic to plan-retrospective, which the Input Contract forbids it from recomputing

# A prohibition with no producer: plan-retrospective is told not to compute what nobody sends it

## Context

`plan-retrospective`'s Input Contract declares `orchestrated` and `epic` as forwarded runtime inputs and states: *"In finalize-step mode the dispatcher forwards it (resolved once per finalize run at `phase-6-finalize/SKILL.md` Step 3 item 4b.a0); this body MUST NOT recompute it."*

This dispatch carried neither field. The prompt body supplied `name`, `plan_id`, `skills[]`, `workflow`, `session_id`, `WORKTREE` and `iteration` — and nothing else.

## Root cause

The consumer's contract forbids self-resolution; the producer does not produce. A body that obeyed the prohibition literally would have no value for `orchestrated` and would fall through to its default. The default is `false`, and `false` is the branch that writes into the **global lessons store** rather than the epic inbox.

The failure is silent in both directions. No error is raised for the missing field, and the wrong-store write succeeds.

## Proposed action

1. Make the forward unconditional at `phase-6-finalize/SKILL.md` Step 3 item 4b.a0, and assert its presence for every `post_run_review` step.
2. Make the absent field an explicit error in the consumer rather than a default — `orchestrated` has no safe default, because both values name a real and different destination.

## Evidence

- Observed first-hand: this dispatch's prompt body, verbatim, carries no `orchestrated` and no `epic`
- This body resolved them via the user-invocable seam (`request read --section source_id` then `inbox detect`) and got `orchestrated: true, epic: review-apparatus` — so the wrong branch was one default away
- Same shape as the defect the audited plan shipped to fix, one layer up: a state nobody recognises resolving to the benign-looking default
