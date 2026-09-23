envelope_version=1
sender_type=plan
sender_id=plan-lr-07-lessons-verb-routing
epic=lessons-routing
kind=candidate-lesson
created=2026-09-23T06:56:43Z

# Add an optional HEAD-resolve flag to manage-status mark-step-done for post-branch-cleanup steps

component: plan-marshall:manage-status
category: improvement
confidence: medium
source_aspects: llm_to_script_opportunities

## Context

Every `head_dependent` finalize step ordered after `default:branch-cleanup` (`project:finalize-step-review-retrospective`, `plan-marshall:plan-retrospective`, and `branch-cleanup`'s own tail) must resolve `git -C {main_checkout} rev-parse HEAD` in a separate Bash call immediately before its `mark-step-done --head-at-completion {sha}` call, because the worktree is gone by that point and the two calls must not race a concurrent HEAD move. This plan performed the identical two-call sequence 3 times in its post-merge tail alone.

## Root cause

The resolve-then-pass pattern is deterministic and machine-parseable (a plain `git rev-parse HEAD` against a fixed path), but is currently hand-authored at every post-merge call site rather than owned by the script it feeds.

## Proposed action

Add an optional flag to `manage-status mark-step-done` (e.g. `--resolve-head-from {path}`) that, when `--head-at-completion` is omitted, shells the `git rev-parse HEAD` itself against the given path and records the result atomically with the mark-step-done write, removing the two-call pattern for every post-branch-cleanup head-dependent step.

## Evidence

- aspect: llm_to_script_opportunities — "the two-call HEAD-resolve-then-pass pattern repeated across post-merge finalize steps this run (branch-cleanup's own tail, review-retrospective, plan-retrospective) is a small, deterministic, machine-parseable candidate"
