envelope_version=1
sender_type=plan
sender_id=the-comment-pipeline-on-the-way-in
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T16:20:27Z

component=plan-marshall:phase-6-finalize
category=bug
title=Re-stamp the create-pr record when the PR is closed and re-created

# Re-stamp the create-pr record when the PR is closed and re-created

## Context

In the-comment-pipeline-on-the-way-in, the create-pr step recorded `pr_number: 1612` (`display_detail: "#1612"`). The change actually merged as PR #1616 (squash 93f5d7dbd): branch-cleanup logged "PR #1616 enqueued via pr merge-queue and corroborated merged". The plan's step record therefore names a PR that never landed.

## Root cause

When the PR is closed and re-opened as a new PR, the new number reaches later steps but the create-pr step record is never re-stamped. Nothing reconciles the recorded PR against the live PR on the branch.

## Proposed action

Whenever a PR is re-created, re-stamp the create-pr facts. Better still, make branch-cleanup and emit-landing check the recorded pr_number against the PR that actually merged, and fail loudly on a mismatch, so ledgers and landings are stamped from PR state rather than from a stale step record.

## Evidence

- aspect: request_result_alignment: create-pr #1612 vs merged #1616
- aspect: log_analysis: work.log 2026-09-24T07:54:53Z "Created PR #1612"; 2026-09-24T15:59:06Z "PR #1616 enqueued via pr merge-queue and corroborated merged"
