envelope_version=1
sender_type=plan
sender_id=plan-v02-04-adr-corpus-cleanup
epic=lessons-routing
kind=candidate-lesson
created=2026-10-26T09:56:04Z

# Candidate lesson: the ci surface cannot set the squash commit message on the merge-queue path, so the landed commit carries the whole PR body (plan-marshall:tools-integration-ci / phase-6-finalize branch-cleanup)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-04-adr-corpus-cleanup (PR cuioss/API-Sheriff#521, merge f5826465), lessons-capture step.

## Observation

PR #521 was merged by the merge queue. The ci abstraction offers no way to set the squash commit subject and body when the PR enters the queue. The squash commit on `main` (f5826465) therefore carries the entire PR body as its message, including the CodeRabbit-generated summary.

## Why it matters

The `main` history picks up bot-generated text and review boilerplate that does not describe the change. The direct-merge path can set the message; the merge-queue path silently cannot, so the two paths land different history.

## Suggested direction

- Expose a commit-subject/commit-body option on the merge-queue enqueue verb (GitHub supports it through the GraphQL `enqueuePullRequest` / merge-queue settings or the repository's squash-message setting), or
- have finalize rewrite the PR body to the intended commit message before enqueueing, and restore the review-facing body afterwards; at minimum, warn that the queue will use the PR body verbatim.
