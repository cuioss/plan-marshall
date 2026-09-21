envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:30:14Z

component=plan-marshall:manage-metrics
category=improvement
bundle=plan-marshall

# Per-dispatch cache accounting is unmeasured on 41 of 41 rows, hiding the dominant cost term

## Rule

A metric store that records a total but never its decomposition can report that a plan was expensive
and never why. Where the decomposition is the actionable half, an all-rows-unmeasured column is a
measurement gap, not a formatting detail — and it is invisible precisely because the total it sits
beside looks complete.

## Observation

Observed in PLAN `preference-admissibility-prose-vs-auditor-code`, which spent **11,867,144 tokens**
(4.7x its `multi_module + tech_debt` error anchor of 2.5M).

Every dispatch-boundary row recorded by `manage-metrics record-dispatch-boundary` carries all four
token-decomposition columns under `unmeasured_columns`:

```
unmeasured_columns: ["input_tokens", "output_tokens",
                     "cache_read_input_tokens", "cache_creation_input_tokens"]
```

That holds for **41 of 41 rows** across all three dispatching phases — 1 in `4-plan`, 7 in
`5-execute`, 33 in `6-finalize`. The derived block says so plainly:

```
context_position_cost:
  total_rows: 41
  measured_rows: 0
  unmeasured_rows: 41
  by_phase: 4-plan 1/0 unmeasured, 5-execute 7/0 unmeasured, 6-finalize 33/0 unmeasured
  position_multiple: unmeasured
  position_multiple_basis: unmeasured
```

And the aggregate mirrors it: `totals_billing_weighted_total: 0` with
`totals_billing_weighted_total_population_count: 0` — a zero over an empty population, which the
store labels honestly but which reads as a cost of nothing.

`total_tokens` and `tool_uses` ARE recorded on every row. So the rows are being written; it is
specifically the four-way split that never lands.

## Why it matters here rather than in general

Context re-read, not generation, is where the billing weight sits — the cache-read share dominates,
and `position_multiple` exists to express exactly that. This plan is the case the metric was built
for: 77% of its 11.9M tokens went to `6-finalize`, concentrated in steps that re-fired 6 to 12 times
each. Whether those re-firings were cheap cache reads or expensive fresh context is the single most
useful thing the retrospective could say about them, and it is the one thing the store cannot answer.

The retrospective can therefore report *that* the plan crossed its error anchor by 4.7x, and cannot
report *what kind* of token it crossed it with.

## How to apply

- **Find where the `<usage>` decomposition is dropped** between the dispatch return and
  `record-dispatch-boundary`. `total_tokens` survives the same path, so the capture point has the
  data in some form.
- **Treat 0-of-N measured as a reportable condition**, not a silent per-row annotation. A phase whose
  every row is unmeasured should surface once, loudly, rather than N times in a column nobody reads.
- **Do not let `totals_billing_weighted_total: 0` render beside a non-zero token total** without its
  `population_count: 0` companion adjacent; the pair is what stops the zero being read as a cost.
