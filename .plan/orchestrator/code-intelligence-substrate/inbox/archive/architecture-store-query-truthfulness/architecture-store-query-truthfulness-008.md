envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:44:36Z

component=plan-marshall:plan-marshall
category=bug
created=2026-09-15
bundle=plan-marshall

# phase_handshake verify exits 1 twice with no stderr captured

## Context

Two `phase_handshake verify` calls in this plan failed with exit code 1 and an empty stderr excerpt. The script-failure classifier could only bucket them as `script_internal_error` — the residual class for a non-argparse exit-1 — because the failure produced no diagnostic text for it to key on.

## Root cause

The verify path raises without writing a reason to stderr, so the failure carries its exit code and nothing else. Every downstream reader (the classifier, the retrospective, a human tailing the log) is left with "it failed" and no handle on why.

## Solution

Ensure the verify path emits its failure reason on stderr — at minimum the invariant that failed and the two values that disagreed — before exiting non-zero. The handshake already computes both sides of every invariant comparison, so the material is in hand.

## Impact

Lower confidence than the other proposals in this batch precisely because the evidence is thin: two occurrences with no stderr is all the record holds. That thinness is itself the finding.

## Evidence

- aspect: script_failure_analysis — `bug, script_internal_error, plan-marshall:plan-marshall:phase_handshake, verify, exit 1, first_timestamp 2026-09-13T21:36:55Z, occurrence_count 2, stderr_excerpt ""`
