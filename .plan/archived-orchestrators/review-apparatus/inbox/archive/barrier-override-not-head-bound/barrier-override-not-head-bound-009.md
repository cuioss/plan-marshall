envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:20Z

# Order plan-retrospective before branch-cleanup destroys the worktree it reads

component: plan-marshall:manage-execution-manifest
category: bug
confidence: high

## Context

The default `phase_6.steps` ordering places `plan-marshall:plan-retrospective` at position 17, after
`branch-cleanup` at position 16. `branch-cleanup` merges the PR and removes the plan worktree. The
retrospective's footprint-derived aspects read that worktree.

This is not a hypothetical. During THIS plan's own finalize, `project:finalize-step-lessons-housekeeping`
explicitly RETAINED lesson `2026-07-28-19-005` with the note: *"finalize step ordering for
plan-retrospective is unchanged by this plan, so a finalize-pipeline fix still cannot be self-verified by
its own run - directly applicable to THIS plan and uncovered."* The predicted failure then occurred in the
very next post-run step.

## Root cause

Step ordering treats the retrospective as a reporting tail that can run last, but the retrospective is an
*evidence-consuming* step whose evidence is owned by an earlier step's cleanup. Ordering by "what
logically concludes the plan" rather than by "what each step needs to still exist" produces exactly this
class of destruction-before-read.

## Proposed action

Either (a) move `plan-marshall:plan-retrospective` ahead of `branch-cleanup` in the default `phase_6`
step order, or (b) split `branch-cleanup` so worktree removal happens after the post-run review band.
Option (a) is cheaper but changes what the retrospective can see about the merge itself; option (b)
preserves both. Whichever is chosen, the general rule worth codifying is: a step that reads a resource
must be ordered before the step that destroys it, and the manifest composer should be able to assert
that.

**Orchestrator note:** possible overlap with the in-flight plan `post-run-steps-ordered-before-their-evidence`
(worktree present at `.plan/local/worktrees/post-run-steps-ordered-before-their-evidence`). That plan's
title names the inverse polarity, but it may be the same family. Check before staging a duplicate.

## Evidence

- decision.log 08:27:09 — lessons-housekeeping retained `2026-07-28-19-005` naming this exact ordering risk as applicable and uncovered
- execution.toon `phase_6.steps` — `branch-cleanup` at index 15, `plan-marshall:plan-retrospective` at index 16
- aspect: artifact_consistency — the predicted failure realized as a false 0%-recall FAIL
