envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:29:52Z

# check-outline-vs-shipped computes the assessments-store discriminator and never branches on it

component: plan-marshall:plan-retrospective
category: bug
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

On this plan the aspect emitted:

```
assessments_store_present: false
assessments_read: 0
assessed_path_count: 0
comparison: measured
counts.include_unrealised:  count 0, denominator 0
counts.exclude_violated:    count 0, denominator 0
```

`exclude_violated` is what the module docstring calls "the one unambiguously bad
outcome". It was published as a clean zero over a population of zero, labelled
`measured`, under `status: success`.

## Root cause

`load_assessments` returns `(records, store_present)` and its docstring is
explicit: `store_present` "is the discriminator between 'outline recorded no
assessments' and 'the store could not be opened' — collapsing the two would let
an unreadable store report as a plan whose outline assessed nothing, which reads
benign."

`cmd_run` publishes that field and **never reads it**. The `inconclusive` guard
keys solely on `if footprint is None`. So the module's stated promise — "An
unresolvable footprint yields `inconclusive`, never three confident zeros" — is
honoured on the footprint axis and violated on the assessments axis, where the
identical condition (nothing to compare) produces exactly the three confident
zeros the docstring disclaims.

`build_findings` then skips zero-count classes, so the two vacuous zeros emit no
finding at all. The only finding surfaced is the benign
`touched_but_unassessed: 63 of 63 — ordinary discovery, the system working`.

## The generalizable rule

Publishing a discriminator is not reading it. A guard that protects one input
axis does not protect the sibling axis with the same failure mode. When a
function computes a could-not-look flag, grep the consumer for a branch on it
before calling the guard done — and prefer a single `comparison` verdict derived
from *all* inputs the comparison needs, not from the last one that happened to
get a guard.
