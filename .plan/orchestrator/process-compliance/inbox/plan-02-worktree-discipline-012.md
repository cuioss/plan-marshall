envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:09:07Z

component=plan-marshall:manage-tasks
category=anti-pattern
bundle=plan-marshall
created=2026-09-20

# Quote manage-tasks update verbatim; check --help before improvising flags

Argparse rejection in plan-02-worktree-discipline (2026-09-19T16:12:53Z):
`plan-marshall:manage-tasks:manage-tasks update` exited 2 (argparse_other).
Same defect class as the sibling solution-outline rejection the same day:
a plausible-but-undeclared verb/flag form that never reaches the script body.

## Solution

Same rule: verbatim subcommands from `--help` or the executor mapping, no
extrapolated verbs or flags. Probe `--help` when the surface is uncertain.

## Impact

Every `manage-tasks` call site during plan/task orchestration.
