envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:32:31Z

component=plan-marshall:manage-status
category=anti-pattern
bundle=plan-marshall

# manage-status metadata invoked without its required --field at phase-3-outline entry

Source signal: script-failure cluster 3 of 3 on plan `identifier-vocabulary-decision`
(epic `orchestrator-refactor`). Work-log marker, `2026-09-19T14:54:03Z`:

```text
[ERROR] (plan-marshall:execute-script:2) script_failure
notation=plan-marshall:manage-status:manage-status exit_code=2
failure_kind=argparse_rejection
detail=Add the required flag(s) to `plan-marshall:manage-status:manage-status
       metadata`: ['field']
```

Fired 10 seconds after `[STATUS] (plan-marshall:phase-3-outline) Starting outline
phase` and immediately before `Starting outline: track=complex, ...` — i.e. during the
outline phase's entry reads, where the agent reads plan metadata to establish track /
domains / compatibility. The retry succeeded; the phase proceeded normally.

## The shape

`manage-status metadata` is one of the **mode-flag-plus-field** surfaces: the read is
`metadata --plan-id X --get --field F` and the write is
`metadata --plan-id X --field F --value V`. The failure is a call that supplied the
mode but not the field it operates on. This is the fifth of the documented
argparse-rejection recurrence signatures (missing required flag), and it is the
lowest-severity of this run's three clusters: self-announcing, instantly recoverable,
no state touched.

## Why it still rides as a candidate rather than being dropped

⭐ On its own this is noise. Its value is **as the third member of a set**, and the set
is the finding. This run produced three distinct argparse rejections across three
unrelated notations — `manage-status` (missing required flag), `ci` (router flag after
the verb), `merge_lock` (value type disagreeing with the house format) — spread across
phase-3-outline, the merge-queue landing poll, and the lock-reclaim path. Three
independent surfaces, three different argparse failure modes, one run.

That is a population worth counting, and counting it is an orchestrator job because the
denominator is cross-plan: **how many argparse rejections does a typical run in this
epic emit, and is three high, normal, or low?** A per-plan view cannot answer it, and
an uncounted "we should be more careful with flags" lesson is exactly the
vacuous-authority generator this corpus keeps re-growing.

⛔ Do not lift this one into the global corpus as a standalone lesson. Either it folds
into a counted cross-plan argparse-rejection-rate observation, or it is dropped. Its
two siblings (messages naming the `ci` and `merge_lock` clusters) carry independent
weight; this one does not.

## Derivation note

All three clusters were read from the plan work log's `[ERROR] ... script_failure`
markers (207 entries, full scan). No `[FAILED]` markers and no
`voluntary_checkpoint → error` reclassifications appeared in this run, so the
three-marker union for this plan is carried entirely by the `script_failure` class.
