envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:21Z

component=project:finalize-step-review-retrospective
category=bug
source_plan=lb-25-phase-and-merge-gates

# Count nitpicks embedded in Actionable-comments review bodies as actionable

## Context

The review-retrospective step for PR #1751 counted CodeRabbit review summary 01db2c as non-actionable because its body opens with "Actionable comments posted: N". That body also carried a nitpick (branch-cleanup.md hardcoding invocation-refusal codes) that triage confirmed and TASK-23 fixed. CodeRabbit's actionable output was therefore under-counted by one (reported 4 actionable instead of 5).

## Root cause

The classifier treats any review body that starts with the "Actionable comments posted" header as a summary-only meta comment, without looking for an embedded nitpick section.

## Proposed action

Parse the review body for embedded nitpick / additional-comment sections and count each as actionable; keep the header-only summary as meta. Add a fixture with a summary that embeds one nitpick.

## Evidence

- aspect: chat_history_analysis - review-retrospective leaf: "One review summary (01db2c) is counted as non-actionable because it opens with the Actionable comments posted: N line. It also contained a nitpick that was confirmed and fixed in TASK-23"
