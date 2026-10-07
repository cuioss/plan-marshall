envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:11:15Z

component=plan-marshall
category=anti-pattern
created=2026-07-29

# A poll loop whose command is malformed is silence, and silence reads as waiting

An orchestrator-authored Monitor polled `ci pr view --pr-number 1044`, but that
verb only accepts `--head`. Every poll exited 2 with empty stdout, was parsed as
`unparsed`, and the monitor would NEVER have fired. PR #1044 merged; the
orchestrator discovered it only because the operator asked " status?".

The failure mode is that a poll loop whose command is REJECTED is externally
indistinguishable from a poll loop whose CONDITION HAS NOT YET BEEN MET. Both
produce no events. The waiting party interprets the absence of events as "not
ready yet" — the most patient and most wrong reading available.

The same run corroborates the flag-shape family independently: `ci pr comments
--pr-number 1044 --plan-id ...` was rejected with exit 2 at 22:37:06Z for the
same class of reason (a verb-scoped flag the subparser does not declare). Across
the whole plan, `script-failure-analysis` classified 11 distinct argparse
rejections — 3 invented_subcommand, 6 invented_flag, 2 missing_required_flag.
Hand-authored poll commands sit on a control path where that ambient error rate
is not survivable.

## Impact

Two rules. (1) A poll loop MUST distinguish "command failed" from "condition not
met": a non-zero exit or unparseable output is an ERROR event that fires the
monitor immediately, never a silent continue. (2) A hand-authored poll command
must be validated once, eagerly, before the loop starts — run it a single time
and assert exit 0 with parseable output; if that probe fails, the loop must not
begin. Absence of events is only meaningful evidence once the command that
produces them is known to work.
