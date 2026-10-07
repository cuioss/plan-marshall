envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:56:38Z

component=phase-3-outline
category=bug
created=2026-07-29

# A plan's own worked example can skip the invariant its neighboring row applies

The plan's own `pre-submission-self-review` caught a real defect the plan itself
introduced: `resolve-command.md`'s derive worked example computed
`module-tests`' bound from the learned value alone (203 x 1.25 = 254, buffered
to 284), skipping the `max(inner, min_timeout)` floor clamp that the `compile`
row one line above the same table correctly applies. The correct buffered value
is 360. Fixed in commit `63d9a1a63`.

## Impact

A worked-example table with multiple rows applying the same formula is a
self-consistency check: if one row applies a clamp/floor and a neighboring row
in the same table does not, that is a defect signal worth checking even when
the doc "looks" internally consistent at a glance — verify every row applies
every step of the documented formula, not just the row being edited.
