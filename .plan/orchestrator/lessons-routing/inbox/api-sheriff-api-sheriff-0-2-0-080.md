envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-11-03T08:18:46Z

# Recurrence: `ci pr wait-for-queue-settle` returns `status: error` on a transient read failure while the PR has merged

Source: API-Sheriff PLAN-V02-55 (`plan-v02-55-it-concurrency-and-local-image-hazard`, PR #558), phase-6-finalize merge step. Component: `plan-marshall:tools-integration-ci` (`pr wait-for-queue-settle`).

Recurrence of the lessons-routing late-arrival item "transient GraphQL read in `wait-for-queue-settle`" (lessons-archive INDEX, "Late arrivals 2026-10-12", messages 135..143, graded medium).

## Observation

`ci pr wait-for-queue-settle` returned `status: error` with `pr_read_failed` / "Not authenticated" after 8 polls. The PR had in fact merged (merge commit d70d2f16 on main). An immediate retry settled `merged` in one poll.

## Why it matters

The verb is the merge step's authority on whether the merge landed. One failed read ended the whole wait as an error, so a successful merge was reported as a failure and needed an orchestrator retry to come out right.

## Suggested direction

Treat a read failure inside the poll loop as a transient poll result (retry within the remaining budget) and return `error` only when reads keep failing until the budget runs out. Report the count of failed reads in the result. Note the possible link to the known cwd effect where `ci` reports "Not authenticated" when run from a removed worktree. That effect could not be confirmed here, since the wait ran before branch cleanup.
