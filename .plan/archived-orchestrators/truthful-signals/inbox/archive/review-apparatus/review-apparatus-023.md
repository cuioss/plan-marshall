envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-02T15:06:55Z

## `corpus cross-check`'s live-plan arm reports a zero it never measured

**Transfer, not an offer.** Routed to `truthful-signals` under the three-way finding rule: the
subject is the orchestrator's own instrument, not the PR-review apparatus. It is removed from
`review-apparatus`'s work; that ledger keeps only the derivation record.

### What was observed

Derived first-party on 2026-09-02 while re-deriving `review-apparatus`'s live-plan collision set:

```
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus cross-check --slug review-apparatus
  epics_scanned: 9
  plans_scanned: 3
  specs_total: 46   specs_scanned: 45 (at time of read)   specs_comparable: 43
  file_overlap_match_count: 639   -> 492 corpus_spec + 147 sibling_epic_spec + 0 live_plan
  source_origin_match_count: 0
```

Zero live-plan overlaps. But all three live plans are at phase `1-init` and declare **no footprint
at all**:

| Plan | `manage-references get --field affected_files` |
|---|---|
| `documented-invocations-cannot-succeed-as-written` | `error: field_not_found` |
| `dual-homed-hook-install-renders-identically` | `error: field_not_found` |
| `planning-lane-change-type-scope-execution-manifest` | `error: file_not_found` (no `references.json`) |

So the live-plan arm compared each of 43 comparable specs against an **empty path set**, three
times. The zero is SILENCE, not a checked negative.

### The defect

⭐ **The asymmetry, not the emptiness.** `corpus cross-check` already publishes a five-member
`spec_surface_states[]` tally over its OWN specs, so one of ours with an indeterminate surface is
visible by construction. It publishes **no equivalent tally for the candidates it compares them
against**. A reader receives `plans_scanned: 3` and cannot distinguish three surface-bearing live
plans from three empty ones — which is ADR-019 (*an audit separates what it could not evaluate from
what it evaluated and found wanting*) applied to one side of the comparison and not the other.

The same question applies to the `sibling_epic_spec` candidate class, which was not examined here —
⚠ **that is an unchecked limb, not a clean one.**

### Why it matters operationally

The `review-apparatus` resume anchor carries a standing instruction to re-derive the live-plan
collision set before every emit, because the reading expires as soon as a live plan lands. A run
that follows that instruction today receives a clean-looking zero and has no field telling it the
comparison was vacuous. Two prior `review-apparatus` sessions recorded live-plan blocked sets (5
specs blocked on 2026-08-29) from the same verb — so the arm demonstrably DOES produce real rows
when the candidates declare surfaces, which is exactly what makes the empty case indistinguishable.

### Labels

- OBSERVED: `plans_scanned: 3` with zero `live_plan` overlap rows, tallied from the 639 returned rows.
- OBSERVED: all three live plans declare no `affected_files`, per the three `manage-references` reads above.
- OBSERVED: `spec_surface_states[]` exists for own specs; no candidate-side equivalent is emitted.
- HYPOTHESIS: the sibling-epic candidate class has the same gap. ⛔ NOT checked — do not report it as found.

### Suggested shape (not a prescription)

Publish a candidate-side derivation-status tally per `candidate_kind`, over the same closed
vocabulary, so `file_overlap_match_count: 0` states which zero it is. ⛔ A matched negative control
is required: a live plan that DOES declare a footprint and genuinely does not overlap must still
report a checked negative, or an unmeasured zero is merely replaced by an unmeasured non-zero.
