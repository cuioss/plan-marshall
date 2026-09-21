envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:12:58Z

component=plan-marshall:manage-tasks:manage-tasks
category=bug

# Quote manage-tasks batch-add verbs from argparse choices

Source: work-log script_failure 2026-09-16T12:15:08Z, notation plan-marshall:manage-tasks:manage-tasks exit 2 argparse_rejection with bracket tokens [domain:..] [profile:..] [deliverable:..] [origin:..] [description:..].

Defect: verification-feedback composed a plausible batch-add invocation carrying bracketed attribute tokens the parser does not declare, so the call never reached the script body.

Rule: quote subcommand and flag names verbatim from the executor mapping or --help; never extrapolate bracket-style attribute arguments from workflow prose.

Evidence: follow-up batch-add calls for TASK-007 through TASK-010 succeeded once the verbatim form was used.
