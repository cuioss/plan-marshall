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

**Ordering note**: the invariant treats the list as a set, so declared
order is informational only. The execution order is still governed by
the `steps` list in `phase-6-finalize` config.

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
