envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:08:53Z

component=plan-marshall:manage-status
category=bug
bundle=plan-marshall
created=2026-09-20

# manage-status transition internal error under worktree-discipline run

Script-internal error in plan-02-worktree-discipline (2026-09-19T17:45:30Z):
`plan-marshall:manage-status:manage-status transition` exited 1
(script_internal_error, not an argparse rejection). The surrounding run
continued, so the transition failure was a silent state-machine gap rather
than a loud usage error.

## Solution

Treat exit 1 from `manage-status transition` as a defect signal worth a
lesson: capture the stderr/exit context at the call site and route the
remediation (phase-guard precondition vs status document shape) explicitly
instead of continuing past an un-transitioned phase.

## Impact

Phase-transition reliability for any plan driving `manage-status transition`.
