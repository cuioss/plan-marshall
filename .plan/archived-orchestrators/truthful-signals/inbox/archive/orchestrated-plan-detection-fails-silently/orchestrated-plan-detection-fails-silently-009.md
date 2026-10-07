envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:16:25Z

component=plan-marshall:workflow-integration-git
category=bug
bundle=plan-marshall

# worktree-remove hardcodes a 60-second inner git timeout that a venv-bearing worktree cannot meet

## What happened

At branch-cleanup on PLAN-114 the `worktree-remove` verb failed **twice** with `git timed out after 60 seconds` — its own hardcoded inner ceiling — leaving a partially-completed removal. The plan directory had already been moved back to main, and the only worktree diffs were the interrupted removal's own deletions.

Recovery required the doc-sanctioned manual path: `git worktree remove --force` under a 600-second Bash timeout, which succeeded.

## Root cause

The 60-second inner ceiling is a fixed constant applied to an operation whose cost scales with the *contents* of the worktree. A plan-marshall worktree carries a bootstrapped pyprojectx venv — tens of thousands of files — and `git worktree remove` must stat and unlink all of them. Sixty seconds is comfortable for a source-only worktree and not remotely enough for one that has run a build.

Since every plan that runs `module-tests` or `verify` in its worktree bootstraps that venv, the ceiling is wrong for the *common* case, not an edge case.

## Why it matters for truthful signals

The first failure is loud, but the state it leaves is quiet and dangerous: a **partially-completed removal**. The verb reported a timeout, not a partial mutation, so the recorded signal ("timed out") understates what happened ("timed out, and left the tree half-deleted"). A caller that retried naively — or that read "timeout" as "nothing happened" — would be reasoning about a tree that no longer matches its mental model.

The project already carries a standing rule that an implausible duration is itself a failure signal on routed builds. This is the mirror case: an implausibly *short* ceiling manufacturing a failure on an operation that was proceeding correctly.

## Corrective rule

1. **Remove the hardcoded 60s inner git timeout** from `worktree-remove`. Either take the timeout from the caller (the Bash-level timeout already bounds the operation) or scale it — but do not pin a constant to an unbounded-cost operation.
2. **On timeout, report the partial-mutation state**, not just the timeout. The verb knows whether it began unlinking; its TOON must say so, so a caller can distinguish "not started" from "half done".
3. While fixing (1), sweep `workflow-integration-git` for other hardcoded inner timeouts on content-proportional operations (clone, prune, gc, checkout of a large tree).

## Provenance

Observed at 16:02:42, **after** `lessons-capture` closed at 15:41, so this defect had no route to the epic from the run that found it. See the companion candidate-lesson on finalize step ordering.
