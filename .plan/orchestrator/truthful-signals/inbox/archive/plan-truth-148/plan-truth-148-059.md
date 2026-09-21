envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:06:57Z

# Candidate lesson: script-failure cluster — plan-marshall:manage-architecture:architecture (router-flag placement)

- source_signal: script_failure cluster (5 of 9 distinct notations)
- notation: `plan-marshall:manage-architecture:architecture`
- markers: two identical `[ERROR] ... script_failure` lines, ~19 hours apart (00:38 and 19:35)

## What happened

`architecture.py: error: unrecognized arguments: --plan-id plan-truth-148`, with the script's own note attached: "`--plan-id` is a top-level flag and belongs BEFORE the subcommand". The identical mistake recurred nearly a day later in a different phase envelope.

## Candidate rule

`--plan-id` is per-script and POSITIONAL-BY-PARSER: on `architecture` it is a router flag that must precede the verb; on other scripts it is declared on the subcommand and must follow it; on others still it is not declared at all. Never append it by rote. The recurrence at a 19-hour interval shows this is not a momentary slip but a default assumption that re-forms in every fresh envelope — which is why the rule belongs in the persona/workflow text rather than in any one caller.
