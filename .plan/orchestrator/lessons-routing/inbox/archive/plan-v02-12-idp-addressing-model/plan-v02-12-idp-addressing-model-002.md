envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=candidate-lesson
created=2026-10-20T20:29:12Z

# Candidate lesson: ci prepare-body needs --for edit for pr edit, and the plain call silently allocates the create file (plan-marshall:tools-integration-ci)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492), lessons-capture step.

## Observation

To update an existing PR body, finalize called `ci prepare-body` without `--for`. That allocated the scratch file for the **create** consumer, so the subsequent `ci pr edit` did not find a body file for the edit consumer and the call had to be redone with `prepare-body --for edit`.

## Why it matters

The plain call succeeds and returns a path, so nothing tells the caller it prepared the wrong consumer's file. The mismatch is only discovered at the consumer verb.

## Suggested direction

Make `--for` required (no create default), or have `pr edit` name the expected `prepare-body --for edit` invocation in its error when it finds only a create-consumer body file. Document the consumer pairing in the workflow docs that call `pr edit` (finalize PR-body refresh).
