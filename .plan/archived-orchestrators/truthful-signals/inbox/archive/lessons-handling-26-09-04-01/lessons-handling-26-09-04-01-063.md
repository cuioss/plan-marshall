envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:53Z

component=plan-marshall:phase-4-plan
category=bug

# phase-4-plan leaf makes three argparse-rejected calls (manage-plan-documents top-level verb, get-deliverable flag ×2), and repeats one without applying the hint

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15). **Bundles two
inbox messages** (`-011`, `-012`), which share the invocation site and the failure shape. Same shape
as `-045`, which bundled three malformed invocations. Please fold this onto `-045` if that
item tracks a class rather than its three instances.

## Observation

In the phase-4-plan envelope (all within one second-scale window):

1. work.log `61f014` (2026-09-15T09:41:40Z): `plan-marshall:manage-plan-documents:manage-plan-documents`
   exit 2, `argparse_rejection`: "Use a registered verb … ['list-types', 'request']". The request
   read is the `request` noun's `read` sub-verb, and the call used a top-level verb instead.
2. work.log `4256cb`, **twice** (09:41:46Z and 09:41:47Z): `manage-solution-outline get-deliverable`
   exit 2, `argparse_rejection`: "Use a declared flag … ['deliverable-number', 'plan-id']". The
   identical call was repeated one second after the first rejection, without applying the hint.

The log does not record the invented verb or flag spelling. The phase recovered and completed.

## Why it matters

`lessons-capture.md` already warns about the top-level `read` paraphrase. Its recurrence in
phase-4-plan suggests that phase's own prose, or a doc it loads, still presents the request read
or the deliverable read in a non-canonical form. The immediate identical retry is a separate
agent-behaviour signal: the rejection's declared-flag hint was not used.

## Candidate direction

- Audit `phase-4-plan` SKILL.md and the standards it loads for any `manage-plan-documents` read
  without the `request read --section` chain, and any `get-deliverable` spelling other than
  `--deliverable-number`. Replace them with xrefs to the owning skill's Canonical invocations.
- Record the invented token in the `script_failure` log line (the rejected argv), so the next
  occurrence names its source instead of leaving it to be guessed.
