envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:29Z

component=plan-marshall:manage-findings
category=anti-pattern
bundle=plan-marshall

# Script-failure cluster 3 of 4: manage-findings rejected twice — an undeclared list flag, then qgate list missing the required --phase

Two rejections on one notation during the finalize review and triage region:

1. `[ERROR]` `d556e7` at 19:35:13Z — "Use a declared flag for
   `plan-marshall:manage-findings:manage-findings list`: ['any-checkout', 'author',
   'bot-kind', 'file-pattern', 'include-qgate', 'kind', 'plan-id',
   'preference-admissible', 'promoted', 'resolution', 'type']".
2. `[ERROR]` `771256` at 19:47:21Z — "Add the required flag(s) to
   `plan-marshall:manage-findings:manage-findings qgate list`: ['phase']".

The second is verbatim recurrence signature 5 in `persona-plan-marshall-agent`:
`--phase` is REQUIRED on the phase-scoped finding verbs, and the same signature also
warns about substituting `--status` for `--resolution` — a confusion the first
rejection's declared-flag list shows is easy to make, since `resolution` is there and
`status` is not.

Source records: work-log `[ERROR]` entries `d556e7` and `771256`, marker class
`script_failure`. One notation, so one cluster.

## Solution

Two verb-specific facts, both quotable from the rejection messages themselves:

- `manage-findings list` filters on `--resolution`, never `--status`, and its full flag
  set is the eleven names printed above.
- `manage-findings qgate list` requires `--phase` in addition to `--plan-id`. There is
  no all-phases form — enumerate the phases and call once per phase.

## Impact

One of four `argparse_rejection` clusters in this run. The notable fact is that this
one is DOCUMENTED as a named recurrence signature and recurred anyway, in the same run
as three sibling argparse rejections. That pattern argues the remedy is structural
rather than documentary: the guard that would have caught it is a pre-call flag check
against the executor's declared surface, not another prose warning. The
`ARGUMENT_NAMING_*` plugin-doctor cluster guards the AUTHORING side of documented
invocations, but nothing guards an ad-hoc call composed at runtime.
