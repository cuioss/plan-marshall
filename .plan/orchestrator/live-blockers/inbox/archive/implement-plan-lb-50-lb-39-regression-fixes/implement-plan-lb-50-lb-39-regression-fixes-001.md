envelope_version=1
sender_type=plan
sender_id=implement-plan-lb-50-lb-39-regression-fixes
epic=live-blockers
kind=candidate-lesson
created=2026-10-16T16:26:54Z

component=plan-marshall:manage-architecture
category=anti-pattern
title=Pin architecture search invocation to canonical --content flag form

# Pin architecture search invocation to canonical --content flag form

## Context

The retrospective script-failure aspect recorded 6 argparse rejections on plan-marshall:manage-architecture architecture search where callers invented or misplaced flags. The plan still landed clean because each failure was retried with the canonical form, but the waste recurred across phases.

## Root cause

Callers extrapolate flag names from prose instead of the canonical invocation block, and the search verb has no single quoted example at the call site.

## Proposed action

Add one canonical invocation example for architecture search --content to the caller workflow where the drift occurred, quoting the exact argparse surface.

## Evidence

- aspect: script-failure-analysis — 6 invented_flag rejections on architecture search
- aspect: logging-gap-analysis — decision log sparse on flag choice
