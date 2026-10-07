envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:09:00Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
bundle=plan-marshall
created=2026-09-20

# Quote manage-solution-outline get-deliverable verbatim; never paraphrase

Argparse rejection in plan-02-worktree-discipline (2026-09-19T15:56:23Z):
`plan-marshall:manage-solution-outline:manage-solution-outline get-deliverable`
exited 2 (argparse_other). The verb exists in prose-like form, so a
near-miss paraphrase still bypasses the script body with exit 2 and corrupts
downstream behavior silently.

## Solution

Quote the subcommand and flag names verbatim from the executor mapping or
`--help`; when in doubt run `--help` first. Never extrapolate
plausible-sounding verbs from workflow narrative.

## Impact

Every `manage-solution-outline` call site; invented verbs fail closed at the
parser with no body executed.
