envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T11:36:29Z

## Proposed lesson metadata

- `component`: `plan-marshall:manage-execution-manifest`
- `category`: `anti-pattern`
- `title`: A plan surviving its own finalize is not evidence its immunity mechanism works when the plan is outside the drop set

## Observation

This plan shipped a **plan-local lane override** — the mechanism by which a plan
exempts itself from a scope-gated compose-time step drop. The override works
end-to-end and is tested.

But the natural dogfood reading — "this plan's own retrospective survived
finalize, therefore the immunity mechanism works" — is **false**. This plan is
`multi_module`, and `scope_gated_finalize` has **no drop set** for
`multi_module`. There was nothing to be immune from. The retrospective survived
because it was never a drop candidate, not because the override protected it.

## Why this is worth recording

The observation is a live, self-inflicted instance of the epic's theme: a plan
executing its own new mechanism and passing green, where the green says nothing
about the mechanism. The tempting inference is available, plausible, and wrong,
and nothing in the run's output flags it — the retrospective's presence looks
exactly the same whether the override fired or was never consulted.

Compare the known corpus entry: a population-derived detector still needs its
anchor re-checked when the fix widens the population. Same failure mode — the
evidence is real but is evidence of something *else*.

## Rule

When a plan ships a mechanism and then runs under it, state explicitly whether
the plan's own run **exercised** the mechanism, and how that was determined. The
test is not "did the run pass" but "**would the run have failed without the
change?**" If the plan's own scope class falls outside the mechanism's trigger
condition, the run is a null observation — say so in the landing rather than
letting a green run be read as a dogfood proof.

Concretely: the immunity mechanism still needs a real exercise under a scope
class that **has** a `scope_gated_finalize` drop set.
