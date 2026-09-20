envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:04:27Z

component=plan-marshall:manage-execution-manifest
category=bug
bundle=plan-marshall

# A plan that renames a step-param key silently breaks its own finalize, because phase-4 froze the old key

## Observation

`one-coherent-automated-review-contract` (PLAN-92) deliverable D3 replaced the `enabled_bots`
config key with `required_bots` / `optional_bots`. The plan's execution manifest was composed at
phase-4-plan (14:13Z), before D3 landed, so `execution.toon`'s
`phase_6.step_params.automatic-review` snapshot froze the now-retired `enabled_bots` key.

At 18:09Z the finalize orchestrator caught it by hand (decision.log `1b633d`):

> Manifest step-params snapshot for automatic-review was frozen at phase-4 carrying the RETIRED
> `enabled_bots` key. Since D3 renames it, the step would have resolved `required_bots` and
> `optional_bots` as absent, yielding empty lists and zero bot gating on this plan's own PR. That
> is exactly the D3 empty-default failure mode.

The failure mode is silent and fail-open: absent keys resolve to empty lists, an empty required-bot
list gates nothing, and `automatic-review` would have reported a clean pass having required no bot
at all. The plan that introduced the empty-default guard would have been the first victim of it.

Corroborating evidence that the old key was still live in the call path: `work.log:20:05:18Z`
records `github_pr fetch_findings` rejecting `--enabled-bots coderabbit,sourcery,pr-agent`.

## Do this instead

- **Reconcile the frozen snapshot against the live schema before phase-6 consumes it.** Add a
  `manage-execution-manifest` verb that diffs the `step_params` key set recorded at phase-4 against
  the step's currently-declared parameter schema, and **fails loud** on a key the plan's own
  footprint retired. This is a deterministic check: both sides are machine-readable.
- **Never let an absent step-param resolve to a permissive default.** An absent `required_bots`
  must be distinguishable from an empty `required_bots`; only the latter may mean "gate nothing".
- Generalize: any plan whose footprint touches the config schema that its own finalize reads is in
  this hazard class. Phase-4 should mark such a plan and force a manifest recompose after the
  schema-changing deliverable lands.

## Recurrence context

Same family as the known finalize-ordering defect (a plan that fixes a finalize-time component
cannot have the fix exercised by its own finalize). Here the inversion is one step earlier: the
plan's *planning-time snapshot* is stale with respect to the plan's *own output*. Epic theme
`truthful-signals` — the step would have reported a confident clean review having gated on nothing.
