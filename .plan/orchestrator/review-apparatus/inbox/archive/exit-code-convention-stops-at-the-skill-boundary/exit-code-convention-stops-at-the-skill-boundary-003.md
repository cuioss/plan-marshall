envelope_version=1
sender_type=plan
sender_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
kind=candidate-lesson
created=2026-09-06T19:30:48Z

# build_time emits a populated all-zero block carrying no substrate discriminator

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: exit-code-convention-stops-at-the-skill-boundary
source_pr: 1423, 1429

## Context

`analyze-logs` emitted this block for a run that executed 8 builds, 2 of which
failed:

```toon
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
  pass: 0
  error: 0
  timeout: 0
  killed: 0
  status_unknown: 0
```

Nothing in that payload says "unavailable". It reads as a measured, complete,
untroubled result — `killed: 0`, `timeout: 0`, `error: 0` is exactly the signal a
reader uses to conclude the run had no build trouble.

`references/log-analysis.md` **does** carry the discriminator, in a comment:
`build_count: 0 = no ledger rows = build time UNAVAILABLE (absent is not zero)`.
And `references/plan-efficiency.md` instructs the consumer to render
`total_build_seconds` as `unavailable` in that case. But the discipline lives only
in prose that a script consumer never reads, and the field that would carry it
does not exist.

The consequence is not hypothetical: `plan-efficiency` is documented to READ
`total_build_seconds` "verbatim … into its totals", so a `0.0` from a dead oracle
becomes a measured zero in the efficiency record. The largest wall-clock line of
this run — 60.8% of all plan script time — is recorded as having cost nothing.

## Root cause

The `build_time` block is the **only** block in this fragment that reports a count
without publishing the substrate it counted over. Its three siblings in the same
payload all do it correctly:

- `context_position_cost` publishes `measured_rows` / `unmeasured_rows` /
  `no_tool_use_rows` and uses the literal `unmeasured`
- `outline-vs-shipped` publishes `comparison: measured` and withholds counts when inconclusive
- `dispatch_coverage` publishes `evaluated_population` per block
- even `totals_billing_weighted_total: 0` rides with `population_count: 0`

So the project's honest-default convention is established and applied throughout;
`build_time` predates it or was missed by it.

## Proposed action

1. Add a substrate discriminator to the `build_time` block — e.g.
   `build_ledger_state: present | empty | unresolved` plus
   `evaluated_population`, mirroring `dispatch_coverage`.
2. When the state is not `present`, emit `total_build_seconds: unavailable`
   (the literal, as `context_position_cost` already does) rather than `0.0`, so a
   consumer cannot fold it into a total by arithmetic.
3. Suppress the five status counters entirely under a non-`present` state. A
   partition that sums to zero over an empty population asserts a partition that
   was never computed.
4. Add a test asserting that a zero `build_count` never co-occurs with a numeric
   `total_build_seconds`.

## Evidence

- `fragment-log-analysis.toon` — the block above, beside
  `script_cost_rollup.ranked[0] = pyproject_build, 18 calls, 11,246,620 ms, 60.8%`
- `references/log-analysis.md` — the discriminator, present only as a comment
- `references/plan-efficiency.md` § "Absent is not zero" — the consumer-side rule
  with no producer-side field to key on
- Upstream cause filed separately: the change-ledger has accepted no row since 2026-09-04
