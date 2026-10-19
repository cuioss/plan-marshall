envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:06Z

component=plan-marshall:manage-solution-outline
category=anti-pattern

# manage-solution-outline call rejected by argparse for an invented --number flag

Source: script-failure cluster (notation plan-marshall:manage-solution-outline:manage-solution-outline, argparse rejection on `--number`), plan plan-70-plan-instance-alignment.

A deliverable-scoped call to manage-solution-outline passed `--number`, which the subcommand's parser does not declare, and exited with code 2 before the script body ran. This is the "invented flag from surrounding prose" signature from persona-plan-marshall-agent § Never invent script subcommands.

## Rule

Take the deliverable selector flag verbatim from the manage-solution-outline Canonical invocations block (or `--help`), not from the word "number" in the workflow prose. If several manage-* scripts name the deliverable selector differently, an alias or a uniform typed-ID flag (per argument-naming.md) would close the class.
