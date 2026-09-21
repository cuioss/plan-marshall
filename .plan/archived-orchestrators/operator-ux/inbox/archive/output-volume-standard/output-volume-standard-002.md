envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T11:09:48Z

# manage-status read declares only --plan-id and --store, never --phase

component: plan-marshall:manage-status
category: anti-pattern
confidence: medium
source_plan: output-volume-standard
source_aspects: script_failure_analysis

## Context

At `2026-09-03T10:57:21Z`, during the `project:finalize-step-review-retrospective` step, a
caller invoked:

```
manage-status read --plan-id output-volume-standard --phase 6-finalize
```

The executor rejected it with `exit_code: 2`, `reason: unknown_flag`, `rejected: --phase`,
`accepted: plan-id, store`. The caller recovered two seconds later with the bare
`read --plan-id ...` form.

## Root cause

`--phase` reads as a natural narrowing flag for a caller that wants one phase's step records,
and the surrounding workflow prose talks in phase terms throughout. But `read` takes no such
flag: the phase step records are already inside the `metadata.phase_steps` block that the bare
`read` returns, so the narrowing the caller wanted needs no flag at all.

This is the invented-flag half of the documented "Never invent script subcommands" recurrence
signature. It is notable that `plan-retrospective/SKILL.md` Step 1 already carries a dedicated
paragraph warning about exactly this drift on exactly this verb ("Do not extrapolate
`status get`, `manage_status get`, or `manage-status:status`") — and the drift still recurred,
one step earlier in the same finalize phase.

## Proposed action

Two cheap, independent moves:

1. In `manage-status/SKILL.md`, state on the `read` entry that phase-scoped step records are
   returned inside `metadata.phase_steps` and that `read` accepts no `--phase` — naming the
   absent flag is what stops the extrapolation, since a reader who does not see `--phase`
   assumes it was merely elided.
2. Have the executor guard's rejection message suggest the nearest declared form, as it
   already does for the CI router's misplaced `--plan-id`. It has `accepted: plan-id, store`
   in hand; printing the caller's own invocation with the offending flag dropped costs nothing.

## Evidence

- aspect: `script_failure_analysis` — finding 4 of 4:
  `anti-pattern / argparse_other / plan-marshall:manage-status:manage-status / read / exit 2 /
  2026-09-03T10:57:21Z`.
- raw log: `logs/script-execution.log` lines 936-939 carry the rejected argv and the guard's
  `accepted:` list; line 940 shows the corrected retry succeeding in 0.08s.
