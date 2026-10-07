envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:48Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `refresh-path-gate-and-invariant-gaps` (PR #687), original message `refresh-path-gate-and-invariant-gaps-004.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: a loop-back cannot wait for a bot whose workflow trigger set excludes the event it is waiting on

## What happened

The run pushed a commit addressing pr-agent's review feedback, then looped back
to wait for pr-agent to re-review the pushed commit. It never did. One
loop-back iteration was burned before the cause was diagnosed.

pr-agent's workflow triggers on:

- `pull_request: [opened, reopened, ready_for_review]`
- `issue_comment`

and **not** on `synchronize`. `synchronize` is the event a push to an open PR
emits. So a push produces no pr-agent run at all — the wait had no possible
satisfying event, and the loop-back would have spun until its own iteration
budget stopped it, not until the condition was met.

The remedy is an explicit `/review` comment, which fires `issue_comment` and
does reach the bot.

## The reusable rule

> Before waiting on a review bot to re-run, read its workflow's `on:` block and
> confirm it triggers on the event your action actually emits. A push emits
> `synchronize`; a comment emits `issue_comment`. A bot that lists neither will
> never re-run, and "wait longer" is not a recovery — replay cannot converge on
> an event that is not generated.

Generalized: a wait-for-condition loop must be able to name the event that
would satisfy it and the producer that emits that event. If either is
unnameable, the loop is unbounded by construction and should fail fast with a
"no satisfying event" verdict rather than consume iterations.

## Why this belongs with the others in this batch

Same family as the sibling candidate-lessons: the loop-back's "waiting for
review" state read as *a review is in progress* while nothing whatsoever was
in progress. The absence of a run was indistinguishable, from inside the wait,
from a run that had not finished — which is the `not_triggered` observable that
`workflow-integration-github`'s `pull_request_runs` verb exists to expose. This
run did not consult it before waiting.

## Candidate remediations (for orchestrator judgement)

1. **Check before waiting.** Query the PR-wide `not_triggered` observable
   (`workflow-integration-github` → `pull_request_runs`) before entering any
   bot-re-review wait; a bot reported `not_triggered` after a push is a
   fail-fast, not a wait.
2. **Trigger explicitly.** Where a re-review after a push is required, post the
   bot's documented trigger comment (`/review` for pr-agent) rather than
   relying on push-driven re-run.
3. **Record the trigger surface per bot.** The set of events each configured
   review bot responds to is stable, cheap to record once, and is the fact that
   decides whether a push-then-wait is even coherent for that bot.
