envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:59:04Z

component=plan-marshall:manage-references
category=bug

# manage-references read takes exactly one flag and was called with another

Source: script-failure cluster, notation plan-marshall:manage-references:manage-references
(exit_code=2, failure_kind=argparse_rejection). 1 occurrence, 5-execute at 13:27:31,
inside the verification-feedback envelope.

Rejection: "Use a declared flag for `plan-marshall:manage-references:manage-references
read`: ['plan-id']."

## Solution

A one-flag verb drew a second flag. Notable because of WHERE it happened: inside
verification-feedback, the workflow that triages a failed build and allocates fix tasks.
A rejection there costs a round-trip at the moment the run is already recovering from a
failure, and the envelope has the least context to spare.

Worth carrying for the epic: argparse rejections cluster in the recovery and finalize
envelopes rather than in the steady-state task loop, because those envelopes touch the
widest variety of scripts each exactly once.

## Impact

One rejection, in the envelope least able to absorb one.
