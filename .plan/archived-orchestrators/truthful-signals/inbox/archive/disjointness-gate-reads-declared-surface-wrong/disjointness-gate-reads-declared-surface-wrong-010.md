envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:43:57Z

component=plan-marshall:workflow-integration-github
category=anti-pattern
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# reviewed_commit_sha is stamped from the landing HEAD, not from the tree the reviewer read — an assumed value presented as an observed one

## What happened

Finding `6742d8`, PR #1366. CodeRabbit's review body **states its own reviewed
range**: `a1cae610..e7299d8e6` — the CI-red HEAD, before the mypy fix. The producer
nonetheless stamped `reviewed_commit_sha: ba5bd9f27` (the current landing HEAD) on
all 7 filed findings, and credited `coderabbit` as `participated` rather than
`stale`, because CodeRabbit declares no `participation_requires_update` and so takes
no currency test.

The stamp was therefore taken from the HEAD **the plan is landing**, not from the
tree **the reviewer read** — while the reviewer had published the correct value in
its own body.

The consequence was benign this run (none of the 7 findings touch the file the mypy
fix changed), but the stamp asserts a currency no evidence supports, and a consumer
reading `reviewed_commit_sha` cannot distinguish a genuinely-current review from a
superseded one.

## Why it matters — this is a recurrence, not a new class

This epic already carries the rule in another surface: **a PR id must be stamped from
PR state, never from the landing message** (the `ci pr merge` false-green incident,
PR #1081). `6742d8` is the same mistake one field over: a value that is *available
from the authority* is instead taken from *whatever the local pipeline happens to
hold*, and the result is published with no marking that it was inferred.

The defect compounds sibling finding `071a67`: because the stamp is fetch-time rather
than reviewed-tree, a stored refusal notice carries the current HEAD and thereby
suppresses the re-review trigger. The stamp is what makes the refusal-conflation loop
close. Fixing the classification without fixing the provenance leaves the mechanism
half-armed.

## Rule

When the authority publishes a fact, read it from the authority. When it does not,
**record the provenance of the substitute** rather than presenting it as observed.
A field that can be either observed or assumed needs a companion that says which —
an assumed value that is indistinguishable from an observed one is not a value, it
is a guess wearing the field's name.

## Remedy shape

Derive the stamp from the reviewer's own declared range where the provider publishes
one (CodeRabbit does, in its review body). Where it does not, stamp with an explicit
provenance marker (`landing-HEAD-assumed`) so `participated` vs `stale` and the
re-review trigger can both branch on whether currency was actually established.

## Status

`pending` at landing; not fixed in-run.
