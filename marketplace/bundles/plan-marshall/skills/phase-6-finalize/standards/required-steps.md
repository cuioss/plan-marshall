# phase-6-finalize Required Steps

This file declares the canonical list of finalize steps that MUST be
marked done on `status.metadata.phase_steps["6-finalize"]` before the
`phase_handshake` script allows the phase to transition. It is parsed
by the `phase_steps_complete` invariant in
`plan-marshall:plan-marshall:_invariants._parse_required_steps`.

**Format**: one markdown bullet per step name. Lines that do not begin
with `- ` are ignored by the parser. Step names must match the
`--step` argument passed to `manage-status mark-step-done` at the tail
of each corresponding standards document.

**Ordering note**: declared order in this file is informational only.
Runtime execution order is the `steps` list in `marshal.json`, which
`marshall-steward` sorts by each step's `order` frontmatter value when
the list is written. phase-6-finalize iterates that list as written and
does not re-sort or validate ordering at runtime.

## Steps

- commit-push
- create-pr
- automated-review
- sonar-roundtrip
- record-metrics
- archive-plan
- branch-cleanup
- validation
- knowledge-capture
- lessons-capture
