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
Runtime execution order is `manifest.phase_6.steps` (composed at outline
time by `manage-execution-manifest:compose` and stored in
`.plan/local/plans/{plan_id}/execution.toon`). phase-6-finalize iterates
that list as written and does not re-sort or validate ordering at
runtime. The composer applies the per-step `order` frontmatter values
documented on each standards doc when assembling the manifest list.

**Activation note**: presence in this file makes a step REQUIRED for the
`phase_steps_complete` handshake when the step also appears in the
manifest. A step listed here but ABSENT from `manifest.phase_6.steps`
for the running plan is NOT enforced — the handshake checks completion
only for steps that the manifest actually scheduled. The handshake
parser MUST refuse to enforce a step that is not in the manifest;
otherwise a manifest pruning would deadlock the phase transition.

## Steps

- pre-submission-self-review
- commit-push
- create-pr
- architecture-refresh
- automated-review
- sonar-roundtrip
- record-metrics
- archive-plan
- branch-cleanup
- validation
- lessons-capture
