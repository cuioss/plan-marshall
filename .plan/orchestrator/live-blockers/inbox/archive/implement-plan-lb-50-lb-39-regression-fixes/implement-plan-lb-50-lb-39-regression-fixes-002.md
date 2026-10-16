envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-50-lb-39-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T16:27:05Z

component=plan-marshall:plan-retrospective
category=bug
title=Render skipped-status fragments instead of dropping them from report

# Render skipped-status fragments instead of dropping them from report

## Context

Compile-report returned status warning with sections_dropped carrying Permission Prompt Analysis. The fragment existed with status skipped (Claude-only aspect on opencode harness) yet the report dropped it, forcing the retrospective to surface the drop manually.

## Root cause

Skipped-status fragments are treated as renderable payload but the section renderer has no skipped branch, so a present-but-skipped fragment takes the loud dropped path.

## Proposed action

Teach compile-report to render status skipped fragments as a one-line skipped section, keeping sections_dropped for present-and-carrying-payload only.

## Evidence

- aspect: compile-report — sections_dropped Permission Prompt Analysis with status warning
- aspect: permission-prompt-analysis — status skipped with skip_reason harness_not_claude
