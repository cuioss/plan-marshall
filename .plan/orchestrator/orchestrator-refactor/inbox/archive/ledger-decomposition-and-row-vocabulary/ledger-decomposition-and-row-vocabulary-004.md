envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:04:39Z

# Advance local main after sync-baseline so self_review surface can run

component: plan-marshall:phase-6-finalize
category: bug

## Context

In ledger-decomposition-and-row-vocabulary, `finalize-step-sync-baseline` rebased the worktree onto origin/main (3 upstream commits). Then `pm-plugin-development:ext-self-review-plan-marshall:self_review surface` failed twice (20:09 and 20:31) with "local base 'main' sits behind 'origin/main' — refusing to surface a stale scope". The pre-submission self-review envelope was dispatched anyway, so it ran without its deterministic candidate surface.

## Root cause

sync-baseline moves the worktree branch onto origin/main but leaves the local `main` ref behind. The self_review surface correctly refuses a stale base, but nothing earlier in the finalize order advances local main, and the self-review step does not stop on the refusal.

## Proposed action

Either have sync-baseline fast-forward the local base ref when it rebases onto origin/main, or have the self_review surface resolve its base against origin/main. Separately, the pre-submission-self-review step should record the surface refusal as degraded coverage rather than dispatch as though the surface ran.

## Evidence

- aspect: script_failure_analysis — `pm-plugin-development:ext-self-review-plan-marshall:self_review` surface script_internal_error, occurrence_count 2
- aspect: logging_gap_analysis — work.log 20:09:00 and 20:31:24, each followed by a self-review DISPATCH
