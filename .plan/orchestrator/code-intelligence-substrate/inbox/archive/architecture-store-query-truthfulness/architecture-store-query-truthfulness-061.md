envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:58:58Z

component=plan-marshall:manage-status
category=bug

# A finalize step called mark-step-done without the required --outcome

Source: script-failure cluster, notation plan-marshall:manage-status:manage-status
(exit_code=2, failure_kind=argparse_rejection). 1 occurrence, 6-finalize at 12:39:16.

Rejection: "Add the required flag(s) to
`plan-marshall:manage-status:manage-status mark-step-done`: ['outcome']."

## Solution

mark-step-done is the handshake every finalize step closes with, so a rejection here is
the step's completion record failing to be written — the call that MAKES the step count
as run. The workflow docs that own each step state the full invocation including
`--outcome` and `--display-detail`; the omission indicates the call was composed from
memory of the verb name rather than from the step's own documented line.

Worth carrying: the highest-consequence argparse rejections are on the verbs that RECORD
state, because a silent exit 2 there leaves the pipeline believing a step never
completed while the work itself was done.

## Impact

One occurrence, recovered in-run; the failure class is disproportionate to its frequency.
