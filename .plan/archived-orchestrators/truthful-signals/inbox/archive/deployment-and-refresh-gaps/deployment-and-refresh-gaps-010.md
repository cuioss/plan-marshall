envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:43Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `refresh-identity-and-scope-defences` (PR #682), original message `refresh-identity-and-scope-defences-002.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: `adr-propose` writes durable files but declares no `mutates_source`, so `branch-cleanup` would destroy them

**Category**: bug
**Suggested component**: `plan-marshall:phase-6-finalize` (`adr-propose` step)
**Source plan**: `refresh-identity-and-scope-defences` (PR #682)

## What happened

Recorded at `logs/decision.log` `2026-09-01T16:22:38Z`, `[WARNING]`, self-caught:

> TOOLING GAP: adr-propose declares no mutates_source in its frontmatter, so it defaults to
> read-only and the dispatcher's commit instrumentation does NOT commit what it writes. But
> the step DOES write files (four ADRs under doc/adr/), and branch-cleanup removes the
> worktree — so on the default path a step that produces durable artifacts has them destroyed
> before they can land. Committed them explicitly here.

Four ADRs (`doc/adr/0004`–`0007`) were written by the step and were, at that moment, live
only as uncommitted files in a worktree that `branch-cleanup` was ordered to remove. They were
committed by hand. On any run where the operator did not notice, the step would have appeared
to succeed and produced nothing.

## Why this is durable, not incidental

The dispatcher's item 5f reads the **declared** `mutates_source` fact and skips commit
instrumentation (a)–(d) entirely on `false`. The declaration is the whole contract — nothing
observes whether the step actually wrote anything on the `false` path. So the failure mode is
structurally silent for any step whose frontmatter under-declares:

- a `mutates_source: false` step that writes tracked source loses the writes at worktree
  removal, with no error and no finding;
- the loss is invisible in the plan record, because the step's own `mark-step-done` reports
  success.

The inverse defect (a `post_run_review: true` step's post-merge dirty-tracked-path guard) is
already instrumented. The under-declaring direction is not.

## Suggested remedy

1. Upstream: `adr-propose` should declare `mutates_source: true`, or stop writing files and
   emit its proposals as plan artifacts instead.
2. Upstream, structural: before `branch-cleanup` removes a worktree, fail (or warn with a
   finding) when the worktree carries uncommitted **tracked** paths that no step's declared
   `mutates_source` accounts for. The declaration would then be checked rather than trusted,
   symmetrically with the post-run-band guard that already exists in the other direction.
