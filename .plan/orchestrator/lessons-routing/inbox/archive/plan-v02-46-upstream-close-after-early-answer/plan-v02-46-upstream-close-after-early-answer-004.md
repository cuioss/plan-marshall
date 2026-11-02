envelope_version=1
sender_type=plan
sender_id=plan-v02-46-upstream-close-after-early-answer
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T18:04:14Z

# Candidate lesson: ci checks pull-request-runs reported has_pull_request_run false while PR workflow runs existed (plan-marshall:tools-integration-ci / workflow-integration-github)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-46-upstream-close-after-early-answer (PR cuioss/API-Sheriff#513, merge e70743f), lessons-capture step.

## Observation

`ci checks pull-request-runs` returned `has_pull_request_run: false` for PR #513, although pull-request workflow runs existed and CI was green. The pre-merge barrier then had to be passed with `--not-triggered` to proceed.

## Why it matters

The barrier's not-triggered observable is meant to prove that no PR-scoped run exists. A false negative here makes the operator override the barrier with `--not-triggered` on a PR that did run CI, which trains the override as routine and hides the case where CI really did not trigger.

## Suggested direction

Check how `pull_request_runs` matches runs to the PR (event type, head SHA vs merge ref, `pull_requests[]` being empty on runs from fork or merge-queue contexts, pagination). Add a fixture where runs exist for the head SHA but `pull_requests[]` is empty, and fall back to head-SHA matching.
