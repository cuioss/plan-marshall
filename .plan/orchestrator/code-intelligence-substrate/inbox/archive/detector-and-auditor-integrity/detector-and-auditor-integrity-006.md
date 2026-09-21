envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:29:54Z

# The zero-attribution probe reads a population LABEL, not a population SIZE

component: plan-marshall:plan-retrospective
category: bug
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

`compile-report` returned `sections_unattributed_zero[0]` — empty — on a run
carrying three fragments whose zeros are exactly the ambiguity the probe exists
to report:

| fragment | shape | why it should have been flagged |
|---|---|---|
| `outline-vs-shipped` | `count: 0, denominator: 0, population: certain_exclude_assessed_paths` | names a population that is EMPTY |
| `direct-gh-glab-usage` | `counts: {total: 0, by_surface: {log_leak: 0, diff_leak: 0}}` | bare integers, no population anywhere |
| `wrapper-tangle` | `counts: {total: 0, by_surface: {wrapper_tangle: 0}}` | bare integers, no population anywhere |

## Root cause

`_counts_names_population` returns `True` **unless** every structured `counts`
entry declares a status in `ZERO_DECLARED_UNMEASURED_STATUSES`. Its own docstring
states the breadth is deliberate: "A `counts` block of BARE integers declares
nothing either way ... Only an explicit self-declaration narrows the answer."

The consequence is that the probe recognises exactly ONE shape — the all-entries-
declare-`not_evaluated` shape of the log-less `check-dispatch-audit` fragment it
was derived from. Every other vacuous zero clears it.

For `outline-vs-shipped` the miss is sharpest: `denominator: 0` is sitting in the
same dict, one key away from `population`, unread. The probe asks whether a
population was NAMED and never whether it was NON-EMPTY.

## The generalizable rule

A detector fitted to the single instance that motivated it will pass every other
instance of the same class. When the discriminator is "did this count come from a
real evaluation", read the SIZE that is already published (`denominator`,
`evaluated_population`) — a label is a claim, a denominator is a measurement.
Validate a new probe against a corpus of existing producers, not against the one
fragment that prompted it: two of the three fragments it cleared here are
first-party producers that ship with the skill.
