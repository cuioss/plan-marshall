envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=candidate-lesson
created=2026-09-07T15:17:33Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
confidence=high
source_plan=plan-130-sweep-the-prose-the-widened-rules

# Surface self-review candidates against origin/main, never the local main ref

## Context

The pre-submission self-review surfacer first computed its candidate set against the local `main` ref, which was stale relative to the remote. It reported a 188-file surface carrying 256 candidates. Re-run against `origin/main` the same surfacer reported the true 112-file surface carrying 4 candidates — a 64x inflation in the candidate count and a 76-file inflation in the scope.

The 76 phantom files were exactly the two upstream commits the finalize rebase had folded into the branch (`de10dfa97` and `ef129d6a3`) — changes the plan did not author and had no business reviewing.

The error was caught only because someone compared `main...HEAD` against `origin/main...HEAD` by hand. Nothing in the surfacer or the step around it flagged the discrepancy.

## Root cause

The surfacer resolves its base ref by name (`main`) rather than by remote-tracking ref (`origin/main`). In a worktree that has just rebased onto fetched upstream commits, the local `main` ref can lag the remote by arbitrarily many commits, and every one of those commits' files enters the review surface as though the plan had written them.

## Proposed action

Resolve the self-review base ref as `origin/{base_branch}` rather than the bare branch name. Where a local ref must be used, verify it is not behind its upstream first and fail loudly rather than surfacing against a stale base. A surfacer that silently reviews 76 files the plan did not touch is worse than one that refuses.

## Evidence

- decision log 2026-09-06T21:11:48Z — "Surfaced at full scope over 112 files against origin/main; the earlier 188-file surface used the stale local main ref and included 76 files from the two rebased-in upstream commits this plan did not author."
- aspect: chat_history_analysis — the correction is recorded as an in-run fix, not as a caught-by-tooling event.
- The final step outcome reads "4 candidates examined, no check matched" — the correct surface. Had the stale run not been caught, the step would have graded 256 candidates over a surface two thirds of which was someone else's work.
