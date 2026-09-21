envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:06:22Z

component=plan-marshall:manage-logging
category=bug
bundle=plan-marshall

# `manage-logging read --phase` is a silent no-op on the work log — it returns unfiltered entries as if filtered

## Observation

`manage-logging` SKILL.md documents `--phase` on the `read` verb as "Filter by phase (work/decision
logs only)". Probed against `one-coherent-automated-review-contract`:

```
read --type work --phase 5-execute --limit 20   -> 20 entries, ALL of them 6-finalize entries
read --type work --phase 3-outline --limit 5    -> 5 entries, ALL of them 6-finalize entries
read --type work --phase 6-finalize --limit 60  -> 60 entries, the tail of the log
```

Every call returns `status: success` with `total_entries: 385` and a slice of the log **tail**,
regardless of the `--phase` value. The filter never narrows anything on the work log; it silently
degrades to "most recent N entries". A caller asking for 3-outline entries receives 6-finalize
entries and has no signal that the filter did not apply.

(The decision log behaves differently again — `read --type decision --phase 1-init` returned
`total_entries: 0`. So the same flag yields "everything, unfiltered" on one log type and "nothing"
on another, and neither answer is correct.)

## Why it matters

This is a load-bearing read path for the retrospective itself: `plan-retrospective` and the
`audit-archived-plan-retrospectives` checks read phase-scoped log slices to attribute behaviour to
phases. A silent no-op means any per-phase log analysis built on this verb has been analysing the
wrong entries — and reporting confidently on them. In this retrospective the defect was only caught
because the returned entries were visibly from the wrong phase.

## Do this instead

- **Fix the filter** so `--phase` narrows on the work log, keyed on a real phase attribution
  (the `(plan-marshall:phase-N-...)` caller token in the message, or an explicit phase field).
- **If a phase cannot be attributed for an entry, say so** — return `filtered: false` plus a reason,
  or error. Never return unfiltered rows under a filtered query.
- Add a regression that reads a plan fixture with entries in ≥2 phases and asserts every returned
  row for `--phase X` belongs to phase X, and that the two log types agree on semantics.

## Recurrence context

Epic theme `truthful-signals`, `vacuous guard` archetype applied to a query rather than a gate: the
filter parameter is accepted, echoed as success, and has no effect. The dangerous property is that
the caller gets plausible-looking data rather than an error, so the failure is invisible until
someone notices the rows are from the wrong phase.
