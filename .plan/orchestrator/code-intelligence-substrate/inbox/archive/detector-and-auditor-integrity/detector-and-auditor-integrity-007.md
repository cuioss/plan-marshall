envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:29:59Z

# The Phase Dispatch Boundaries section is triggered on a key no producer publishes at bundle top level

component: plan-marshall:plan-retrospective
category: bug
severity: warning
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

`compile-report` placed **Phase Dispatch Boundaries** in `sections_omitted` — the
benign half — on a run whose `log-analysis` fragment carries a fully populated
`dispatch_boundaries` block: three phases (`4-plan`, `5-execute`, `6-finalize`),
all with `present: true`, holding 33 rows with termination causes, token totals,
tool uses and durations.

## Root cause

`should_emit` resolves the trigger with `fragments.get('dispatch_boundaries')` —
a lookup at the TOP LEVEL of the fragment bundle. The only producer of that data
is `analyze-logs`, which nests it inside the `log-analysis` fragment. No bundle
key `dispatch_boundaries` exists, so `_dispatch_boundaries_has_present_phase`
receives `None`, returns `False`, and the section is omitted.

Because the fragment the omit-branch inspects (`fragments.get(fragment_key)`) is
also absent, `_renders_usable_body` is False and the section takes `omitted`
rather than `dropped`. The loudness machinery is intact; it is looking at the
wrong object.

## Why it matters here specifically

The omitted section is the one carrying the dispatch-termination distribution —
which on this plan showed that 10 of 14 phase-5 terminations were
`voluntary_checkpoint`, the finding that explains six of the nine operator turns.
The single most behaviourally significant table in the retrospective was dropped
and reported as "nothing to lose".

## The generalizable rule

A trigger key must be resolved against the shape the producer actually writes.
When a section's data is nested inside another aspect's fragment, either lift it
at compile time (as `_footprint-derivation` is) or point the trigger at the
owning fragment. A structural test that registers the real producer output and
asserts the section appears in `sections_written` would have caught this; a test
that hand-builds a top-level `dispatch_boundaries` key cannot.
