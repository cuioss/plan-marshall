envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:27:31Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
confidence=medium
title=Argparse rejections recur across 10 scripts despite the executor already naming the fix

# Argparse rejections recur across 10 scripts despite the executor already naming the fix

## Context

This plan recorded 20 script failures, 12 unique, spread across 10 distinct script
notations. The dominant class is argparse rejection, not script-internal error:

- `argparse_other` on `manage-logging decisions`, `manage-solution-outline get-deliverable` (x4),
  `manage-references read`, `manage-findings qgate` (x4), `manage-metrics record-dispatch-boundary`,
  `ci --plan-id`, `manage-config plan` (x2), `manage-status get-phase-steps` (x2)
- `invented_flag` on `manage-change-ledger query` and `architecture search`
- one doubled-notation error: `plan-marshall:manage-change-ledger:manage_change_ledger`

The retrospective agent writing THIS report added a 21st in the same class, calling
`manage-solution-outline extract-deliverables` (the canonical verb is
`list-deliverables`) — which is worth recording precisely because it happened while
holding the hard rule "Never invent script subcommands" in context.

The `ci --plan-id` rejection is the router-scoped-flag signature the persona doc already
enumerates as one of its five canonical recurrence signatures.

## Root cause

This is an adherence gap, not a tooling gap, and the distinction matters for the remedy.
The executor already returns everything needed to self-correct on rejection: it names
the rejected verb, lists the accepted set, and suggests the nearest canonical form. A
`recipe-fix-argparse-rejection` skill already exists. The failure is that the verb is
guessed from surrounding workflow prose before the accepted set is consulted, and the
prose plausibly suggests a name argparse does not declare.

Note the shape: `get-deliverable` (x4) and `qgate` (x4) each repeated FOUR times. A
rejection that repeats four times is not a typo; it is a call site being re-attempted
without reading the rejection payload.

## Proposed action

Do NOT propose a new validation script — that would duplicate what the executor already
emits. Instead:

1. Add the observed signatures to the persona doc's recurrence-signature table where
   they are not already present, keyed on the concrete invented-vs-canonical pair.
2. Consider a cheap structural guard: when the same notation+verb is rejected more than
   once in a plan, the executor could escalate its message (the repeat is the signal).
3. Worth measuring across the corpus before acting: whether the 4x repeats concentrate
   in workflow docs whose prose names a verb the script does not declare. If so the fix
   is at the doc, and `ARGUMENT_NAMING_*` plugin-doctor coverage is the enforcement point.

## Evidence

- aspect: script_failure_analysis — 20 total failures, 12 unique, 10 distinct components, with per-signature stderr excerpts
- occurrence counts: `get-deliverable` 4, `qgate` 4, `manage-config plan` 2, `get-phase-steps` 2
- first-party: this retrospective's own `extract-deliverables` rejection, recorded rather than quietly retried
