envelope_version=1
sender_type=plan
sender_id=plan-v02-04-adr-corpus-cleanup
epic=lessons-routing
kind=candidate-lesson
created=2026-10-26T09:55:42Z

# Candidate lesson: a fork or dispatched leaf cannot dispatch the review verifiers, so finalize review rounds must be orchestrated from the main context (plan-marshall:phase-6-finalize functional-review / code-review)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-04-adr-corpus-cleanup (PR cuioss/API-Sheriff#521, merge f5826465), lessons-capture step.

## Observation

The functional review and the code review each require a second dispatched party (the verifier) before the round may close. When the finalize pipeline itself ran inside a fork or a dispatched execution-context leaf, the verifier dispatch was impossible: a leaf cannot spawn subagents. The rounds could only be closed by moving the review orchestration back to the main context. This plan spent 7 functional-review firings and 4 code-review firings; each verifier hop had to originate from the main context.

## Why it matters

The workflow docs describe the verifier as "always dispatched from the inline context", but nothing stops finalize from being driven from a fork or leaf. The run then reaches the review step and stalls at the verifier, or the author is tempted to self-verify.

## Suggested direction

- Fail fast at finalize entry (or at the review step) when the caller is a leaf/fork: return a structured "review round needs main-context orchestration" signal naming the author and verifier dispatches owed, instead of discovering it mid-round.
- State in the phase-6-finalize entry contract that the review steps are orchestrator-owned and cannot run inside a dispatched finalize driver.
