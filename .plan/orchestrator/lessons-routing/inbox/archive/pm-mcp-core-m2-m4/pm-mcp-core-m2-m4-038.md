envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T20:00:36Z

# Refresh manifest step params when the plan itself changes marshal.json

**Component**: `plan-marshall:manage-execution-manifest` (compose and step-params snapshot)
**Category**: improvement
**Confidence**: high
**Signal source**: plan-retrospective (chat history, request-result alignment), plan-38-review-bot-re-review

## Context

This plan changed a finalize step parameter (`re_review_on_loopback` of `plan-marshall:automatic-review`) in `.plan/marshal.json`. The execution manifest copies the finalize step parameters when phase 4 composes it, which is before phase 5 makes the change. Finalize would therefore have run on the old value `false`, and the behaviour this plan existed to prove would have been silently absent on its own PR. The outline caught this and added a manual mirror step, `manage-execution-manifest step-params set ... --value true`. That step then hit the empty-`--value` argparse defect once, which lessons-capture has already reported.

## Root cause

The manifest copy of the step parameters is taken once, at phase 4, and is never compared with `marshal.json` again. A plan whose footprint includes `.plan/marshal.json` runs finalize on stale configuration unless the outline happens to notice.

## Proposed action

At the start of finalize, when the realized footprint includes `.plan/marshal.json`, re-read the finalize step parameters from the worktree's `marshal.json` and reconcile the manifest copy. Log every parameter that changed. Alternatively, have phase-3-outline flag this case automatically so it does not depend on the outline noticing.

## Evidence

- chat_history_analysis: the outline hand-back says "The plan's execution manifest stores the step parameters when phase 4 composes it. That happens before phase 5 changes the value, so this plan's copy would still say `false`"
- request_result_alignment: the manual mirror was folded into deliverable 1 as an undeclared follow-up step

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-38-review-bot-re-review-006.md` from plan plan-38-review-bot-re-review (PLAN-38, #24)
