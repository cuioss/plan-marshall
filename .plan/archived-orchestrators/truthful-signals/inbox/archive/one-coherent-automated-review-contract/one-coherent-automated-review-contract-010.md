envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:05:14Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# The plan-efficiency budget anchor table is keyed on vocabulary no producer emits, so it can never match

## Observation

`references/plan-efficiency.md` § 2 defines a 12-row calibration table keyed on
`(scope_estimate, change_type)`, and § 3 makes finding emission MANDATORY when a row's threshold
trips. Checked against the actual producers, **no plan can ever match a row**:

**`change_type` axis** — the producer enum is fixed by
`manage-status change-type-heuristic --help`: `feature, bug_fix, tech_debt, enhancement,
verification, analysis`. The table only has rows for `bug_fix`, `feature`, and `refactor`.
- `refactor` is not in the producer enum at all, so 3 of the 12 rows (`surgical+refactor`,
  `single_module+refactor`, `cross_cutting+refactor`, `complex+refactor` — 4 rows) are dead on
  arrival.
- `tech_debt`, `enhancement`, `verification`, `analysis` — 4 of the 6 real values — have no row.

**`scope_estimate` axis** — the value is written to `references.json` by
`manage-status scope-estimate-heuristic`, which documents that it classifies
`surgical | single_module`. This plan's persisted value is `multi_module`, which appears in no row.
The table's `cross_cutting` and `complex` values are not `scope_estimate` vocabulary at all — they
look like `track` vocabulary (`references.track` on this plan is in fact `complex`). The column is
keyed on one field and populated from another field's value space.

Consequence for this plan: `(multi_module, enhancement)` matched nothing, the aspect fell back to
the four generic ratio thresholds, and the fallback fired silently — the report shows ratio-based
warnings with no indication that the calibrated budget gate never got a chance to run.

## Do this instead

- **Derive the table's key vocabulary from the producers, not from prose.** Enumerate rows from the
  actual `change_type` enum and the actual `scope_estimate` value space; delete `refactor` rows or
  add `refactor` to the producer enum, and decide explicitly whether the scope axis is
  `scope_estimate` or `track` — then name the column after the field it is actually read from.
- **Make an anchor miss visible.** When no row matches, the fragment MUST record
  `anchor_lookup.matched_row: none` and emit at least an `info` finding saying the calibrated gate
  did not apply. Falling back silently is what let a 100%-dead table survive.
- Add a test that asserts every `change_type` in the producer enum and every `scope_estimate` in
  the producer's value space has at least one matching row — a population-derived detector, per the
  standing rule that every set-guarding check must be derived from the population.

## Recurrence context

Fifth instance of the `vacuous guard` archetype in this corpus, and a textbook
`truthful-signals` case: a precise, authoritative-looking 12-row calibration table, cited by a
MANDATORY emission contract, that has never fired for any plan.
