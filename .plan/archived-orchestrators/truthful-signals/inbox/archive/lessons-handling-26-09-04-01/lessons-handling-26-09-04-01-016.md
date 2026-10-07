envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T06:10:48Z

component=plan-marshall:manage-execution-manifest
category=improvement

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-02
(`inherited-build-config-verification-depth`, merged as PR #714 / `7482cf18`).
bundle=plan-marshall

# A gate with no declared verdict_inputs re-fires on every HEAD advance: 40 minutes for one markdown file

## Observation

This plan's entire footprint is one markdown file (`AGENTS.md`) that matches no
`build_map` glob. The whole-tree quality gate nonetheless ran THREE times —
903 s + 788 s + 710 s, roughly 40 minutes of wall clock — once per review
loop-back.

Two independent mechanisms produced that, and both are individually defensible:

1. **Inclusion.** At phase-4 compose time `build-decision` returns `unknown`,
   because the plan's realized footprint is not yet resolvable. The composer
   fails toward inclusion, so the gate is put in the manifest.
2. **Re-firing.** The gate declares no `verdict_inputs` surface, so
   `verdict_currency` returns `invalidated / verdict_inputs_undeclared` on every
   HEAD advance and the previous green verdict is never reusable.

Composed, they mean: a gate that should not have been included at all is then
re-run in full for every commit the review loop produces.

## The generalisable rule

Fail-toward-inclusion at compose time is only cheap if the included step can
later *retire itself* on evidence. A step that both (a) is included on an
`unknown` and (b) declares no verdict-input surface has no exit at either end —
it cannot be skipped when the footprint resolves, and it cannot be cached when
nothing it depends on changed. The cost is then linear in review rounds, and
review rounds are exactly what a contested plan has many of.

## Suggested corrective action

Either half breaks the multiplication; both are worth having:

- **Re-evaluate inclusion once the footprint IS resolvable.** By phase 5/6 the
  realized footprint is known. A gate included on a phase-4 `unknown` should be
  re-tested against the resolved footprint before its first run, and dropped
  when it matches no `build_map` glob.
- **Declare `verdict_inputs` on the whole-tree quality gate.** Its inputs are
  the source globs it actually builds. With those declared, a HEAD advance that
  touched only `AGENTS.md` leaves the prior verdict current and the gate does not
  re-fire.

## Impact

Roughly 40 minutes of compute per docs-only plan that goes through a multi-round
review, scaling with round count — and, worse, the wait is what pushes an
operator toward force-done shortcuts on the *other* gates.
