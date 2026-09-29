envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=candidate-lesson
created=2026-09-29T13:40:07Z

component=plan-marshall:phase-6-finalize
category=bug

# Restamp the create-pr record when the PR is closed and reopened

## Context

In plan-12-tool-triage the `create-pr` step record in `status.metadata.phase_steps` still reads `display_detail: "#1653"` and `facts.pr_number: "1653"`. The PR that CI verified, reviewed and merged through the queue at 26f864b1e was #1654. The finalize work log records the switch ("SKIP create-pr (done, PR #1654 via close_and_reopen)"), but the step record was never updated, and every later reader of the step facts gets the closed PR's number.

## Root cause

The close-and-reopen recovery (the unattended no-bot-reaction path) creates a new PR number, but nothing rewrites the create-pr step's `pr_number` fact. The step stays `done` and is skipped on re-entry, so its stale fact outlives the PR it names.

## Proposed action

When close_and_reopen yields a new PR, re-record the create-pr step with the new `pr_number` and display detail, or make downstream consumers read the PR number from live PR state instead of the step fact. Add a pre-merge check that the create-pr fact matches the PR being merged.

## Evidence

- status.json phase_steps.create-pr: display_detail "#1653", facts.pr_number "1653"
- work.log 2026-09-29T07:09:01Z: "SKIP create-pr (done, PR #1654 via close_and_reopen)"; 13:27:38Z "PR #1654 enqueued via pr merge-queue and corroborated merged"
