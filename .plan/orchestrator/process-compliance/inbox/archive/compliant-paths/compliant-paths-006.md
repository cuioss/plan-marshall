envelope_version=1
sender_type=plan
sender_id=compliant-paths
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T19:20:39Z

component=plan-marshall:phase-6-finalize
category=best-practice
title=Owed architecture hint: accept transient CI wait-budget lapses on live-pending evidence
status=active

## Candidate lesson (preference-emitter, plan compliant-paths)

Disposition pattern `(plan-marshall:phase-6-finalize, ci-timeout, accepted)`
recurred 3 times within this plan (preference_min_recurrence=2).

## Generalized hint

A `ci-verify` wait-budget lapse is not a red build. When the live `checks
status` shows the workflow IN_PROGRESS with zero failures and the local
whole-tree verify is green on the same HEAD, accept the timeout finding
without opening fix tasks and proceed — the wait budget, not the tree, is
what expired.

## Owed call

`architecture enrich best-practice --module plan-marshall:phase-6-finalize`
