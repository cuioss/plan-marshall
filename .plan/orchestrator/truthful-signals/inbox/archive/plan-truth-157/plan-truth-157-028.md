envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:26Z

component=plan-marshall:manage-execution-manifest
category=anti-pattern
bundle=plan-marshall

# Script-failure cluster 1 of 4: manage-execution-manifest read called with an undeclared flag

At the first phase-5 dispatch of this run, `manage-execution-manifest read` was
invoked with a flag it does not declare. The executor rejected the call with
`exit_code=2`, `failure_kind=argparse_rejection`, and the remediation hint "Use a
declared flag for `plan-marshall:manage-execution-manifest:manage-execution-manifest
read`: ['plan-id']" — the verb declares exactly one flag, `--plan-id`.

Source record: work-log `[ERROR]` entry `fb0b88` at 2026-09-13T22:06:14Z, marker class
`script_failure`.

## Solution

Quote the flag set verbatim from the verb's own `--help` or from the owning skill's
canonical-invocation block before issuing the call. This verb's entire surface is
`--plan-id`, so any additional flag is a rejection.

## Impact

This candidate is one of FOUR distinct failing script notations in this single run,
and all four were `failure_kind=argparse_rejection`:

1. `plan-marshall:manage-execution-manifest:manage-execution-manifest` (this one)
2. `plan-marshall:tools-integration-ci:ci`
3. `plan-marshall:manage-findings:manage-findings`
4. `plan-marshall:manage-architecture:architecture`

The per-cluster records are transmitted separately because the signal is
per-notation, but the orchestrator should judge whether the FOUR-IN-ONE-RUN rate is
the real finding — two of the four are textbook instances of recurrence signatures
already documented in `persona-plan-marshall-agent`, which means the documented guard
did not prevent them. The executor's rejection messages were high quality in every
case (each printed the declared flag set or the corrected invocation), so the gap is
on the call-authoring side, not the diagnostic side.
