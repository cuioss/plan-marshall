envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T17:37:49Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-11-20
bundle=plan-marshall
title=Consume pull_request_cut in finalize to open one PR per recorded cut

# Consume pull_request_cut in finalize to open one PR per recorded cut

## Context

PLAN-V2-158 declared about 152 files against a 100-file pull-request limit. At the outline gate the operator chose "two pull requests from this plan" (PR A = deliverable 1, PR B = deliverables 2 to 6). Phase 4 recorded the cut in `status.metadata.pull_request_cut`, in the task titles and in the decision log, and its leaf noted that no documented finalize consumer reads that field. At finalize the lifecycle could only open one PR from the one branch (126 files), so the operator had to be asked a second time how to make the two PRs ("A first, then B"), and PR A (#525) was produced outside the normal create-pr step.

## Root cause

`create-pr` and `branch-cleanup` assume one plan = one branch = one PR; `pull_request_cut` is written by phase 4 but read by nothing.

## Proposed action

Either let finalize read `pull_request_cut` and drive one create-pr / ci-verify / review / merge cycle per cut (cutting a branch per cut from the deliverable commits), or refuse to record a multi-PR cut at phase 4 and steer the outline gate to the plan-split option instead. Whichever is chosen, the operator should answer the split question once.

## Evidence

- aspect: chat_history_analysis — two operator decisions on the same PR split (outline gate option B, finalize "A first, then B")
- aspect: request_result_alignment — D1 shipped in #525, D2-D6 in #529
- phase-4-plan leaf hand-back — "I found no documented finalize consumer for pull_request_cut"
