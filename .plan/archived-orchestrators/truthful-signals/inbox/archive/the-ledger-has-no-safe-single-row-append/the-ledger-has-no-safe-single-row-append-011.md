envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:22Z

component=plan-marshall:manage-metrics
category=bug
confidence=high

# State which phases an (n=k/N) total covers, not only how many

## Context

This plan's `metrics.md` Total row renders `Tokens` as `5,406,410 (n=5/6)` and `Reported (wall)` as `2h40m (n=5/6)`. Both markers say five of six phases. They are DIFFERENT five-phase subsets:

- The token total covers 2-refine, 3-outline, 4-plan, 5-execute and 6-finalize. It omits 1-init, which dispatched nothing.
- The wall total covers 1-init, 2-refine, 3-outline, 4-plan and 5-execute. It omits 6-finalize, which never closed.

The overlap is four phases, not five. The marker publishes the SIZE of the population and not its MEMBERSHIP, so two columns marked identically are not comparable.

The visible consequence is on the same row: Total Worked reads 3h28m while Total Reported (wall) reads 2h40m. Worked exceeds wall. `plan-efficiency.md` warns that this can happen through two documented clamp escapes, so a reader is primed to attribute it to one of them. Neither applies here. Restricting worked to the wall population gives 5,501s against 9,626s of wall - comfortably inside the invariant. The inversion is entirely the population mismatch, and the caveat text points the reader at the wrong cause.

## Root cause

`{field}_population_count` is emitted per column, and every column divides by the same `totals_population_denominator`. Nothing records WHICH phases each column's count was drawn from, so two counts of equal size read as the same population.

## Proposed action

Publish the member list, not just the count - a `{field}_population_phases` beside each `{field}_population_count`. Then a renderer can mark two totals as non-comparable, and the Worked-exceeds-wall case can be attributed to its actual cause instead of to a clamp escape that did not occur.

## Evidence

- `manage-metrics generate` return: `totals_tokens_population_count: 5`, `totals_wall_ms_population_count: 5`, `totals_population_denominator: 6`.
- metrics.md Phase Breakdown: 1-init row has `-` in Tokens; 6-finalize row has `-` in Reported (wall).
- Totals: `totals_worked_ms: 12520921` vs `totals_wall_ms: 9626000`; 6-finalize worked is 1h57m (7,020s); 12,520.9 - 7,020 = 5,500.9s over the shared five phases, against 9,626s of wall.
- plan-efficiency.md lines 141-142 - the clamp-escape caveat that this case does not match.
