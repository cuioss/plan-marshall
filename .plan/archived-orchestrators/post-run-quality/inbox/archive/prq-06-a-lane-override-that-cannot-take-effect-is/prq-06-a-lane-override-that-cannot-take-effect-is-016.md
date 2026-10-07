envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:46:22Z

component=plan-marshall:manage-execution-manifest
category=bug

# An invariant documented as unconditional was enforced on one of its two live producers

`manifest-schema.md` states, unconditionally, that "a step present in `phase_6.steps` never carries a bare `lane: off` in `phase_6.step_params`". Only the COMPOSE path enforces it. The second producer that can add a step to `phase_6.steps` — `reconcile --apply` — does not, so it can write exactly the two-halves-disagree state the invariant exists to forbid.

## Evidence

`58e257` (6-finalize, `fixed`): `cmd_compose` builds `phase_6_effective_lanes` and passes it to `_snapshot_step_params`. `reconcile --apply` computes `merged = retained + backfill`, writes it to `phase_6['steps']`, and calls `_snapshot_step_params([...], marshal_map)` with **no `effective_lanes` argument** — so the default `None` short-circuits the rewrite and the raw stored lane is copied verbatim. A backfilled step whose merged param object carries `lane: off` lands in `phase_6.steps` AND in `step_params` with a bare `lane: off`.

This is not hypothetical: `required-steps.md` § "Reconciliation Contract" documents `reconcile` as THE one operation permitted to amend the frozen list at finalize entry.

## Rule

An invariant's scope is the set of **writers that can reach the state it forbids**, and that set must be enumerated when the invariant is written. Two questions belong in the same change as any new invariant:

1. Who else writes this field? (Here: one other producer, findable by searching for writes to `phase_6['steps']`.)
2. Does the invariant's wording claim more than its enforcement covers? If enforcement is compose-time only, the prose must say compose-time only.

The failure mode is specific and expensive: a reader trusts the unconditional wording, builds on the guarantee, and the second producer quietly violates it. Either widen the enforcement or narrow the sentence — but never leave a documented-unconditional invariant with a single-producer guard.

## Related shape in the same plan

`420319` is the same species one level out: a sentence in `lessons-capture.md` claimed `_read_frontmatter_lane` was `prunable_when`'s "sole reader" with no scope qualifier, while two live readers existed outside the compose path. Both defects are an absence-or-uniqueness claim written without enumerating the population it quantifies over.
