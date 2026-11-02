envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=candidate-lesson
created=2026-10-20T20:29:04Z

# Candidate lesson: git-workflow commit does not stage files and reports a misleading FETCH_FAILURE when nothing is staged (plan-marshall:workflow-integration-git)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492, merge 03cb4755), lessons-capture step.

## Observation

`workflow-integration-git` `commit` was invoked expecting it to stage the plan's changed files. It does not stage anything. With an empty index the call failed, but the error it surfaced was `FETCH_FAILURE` — a remote/network-sounding classification — rather than "nothing staged". The operator had to diagnose the empty index by hand before staging and retrying.

## Why it matters

The error class points the caller at the remote and the network, which is the wrong place. An empty index is a local, deterministic precondition and deserves its own error (e.g. `nothing_staged`) naming the fix.

## Suggested direction

Either stage the plan footprint (documented, opt-in) or detect an empty index before any fetch/commit step and return a dedicated error naming `git add` / the staging verb. Document clearly in the commit verb contract whether staging is the caller's job.
