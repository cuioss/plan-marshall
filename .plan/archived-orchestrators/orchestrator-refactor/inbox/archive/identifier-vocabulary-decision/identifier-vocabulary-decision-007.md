envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:25:08Z

component=plan-marshall:phase-6-finalize
category=bug
title=A forked finalize subagent inherits a worktree-pinned cwd and cannot finish branch-cleanup

# A forked finalize subagent inherits a worktree-pinned cwd and cannot finish branch-cleanup

## Context

During `branch-cleanup`, a forked subagent reported that its Bash cwd was pinned to `.plan/local/worktrees/identifier-vocabulary-decision` and that `cd` did not persist across calls — confirmed with two clean back-to-back `cd`/`pwd` tests, so a transient race was ruled out. It had already completed `integrate_into_main` (cwd-independent by contract) and was holding the cross-plan merge lock.

Everything remaining needed the main checkout as cwd: `worktree-remove`, `switch-and-pull`, `prune-local-and-remote-ref`, and the whole remainder of the finalize step loop — deploy-target, sync-plugin-cache, review-retrospective, plan-retrospective, lessons-capture, preference-emitter, record-metrics, phase-breakdown, archive-plan. None was reachable. The fork handed control back mid-step, explicitly recommending that the parent resume from `worktree-remove` or that a fresh non-fork agent be spawned with the main checkout as its launch cwd, and warning that forking again from a worktree-pinned context would hit the same wall.

The hand-back left the merge lock held and `branch-cleanup` without a terminal outcome at that moment, both of which the fork correctly flagged.

## Root cause

A fork inherits the parent's pinned cwd, and under the move-based cwd-pinned model that cwd is the plan worktree. `branch-cleanup` is the one finalize step whose later half must run against the main checkout — it is the step that removes the very worktree the cwd points into — so a fork taken at that point is structurally unable to finish it.

## Proposed action

Do not fork across the `worktree-remove` boundary. Either complete `branch-cleanup` in the context that can reach the main checkout, or make the post-`integrate_into_main` half of the step explicitly cwd-independent so the tree it operates on is passed rather than inherited. The failure is deterministic, not incidental, so it will recur on any run that forks at the same point.

## Evidence

- aspect: chat_history_analysis — subagent hand-back reporting the cwd pin, verified with two back-to-back `cd`/`pwd` tests
- the hand-back enumerated the nine remaining finalize steps as unreachable
- merge lock was held at hand-back time (`action: already_held`, `waiting_count: 0`)
