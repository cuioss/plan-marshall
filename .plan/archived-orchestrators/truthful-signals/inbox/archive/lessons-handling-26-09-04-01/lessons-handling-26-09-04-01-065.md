envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-16T15:33:07Z

component=plan-marshall:plan-orchestrator
category=bug

# corpus cross-check counts overlaps against TERMINAL and closed-epic specs, so a literal reading of the disjointness gate blocks every late plan in a maturing epic

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01` on 2026-09-16. **Found by the
orchestrator itself while running `next`**, not by a plan — which is why it took ten plans to surface:
it only bites once an epic has a substantial shipped corpus.

## Observation

`workflow/orchestrate.md` Step 4 states the disjointness half as:

> A candidate is disjoint **iff** its `corpus surfaces` row carries `admits_disjointness_check: true`
> AND `corpus cross-check` reports no `file_overlap_matches[]` row naming that candidate's spec.

`corpus cross-check` compares a candidate against three populations — sibling epics (**active and
archived**), the live plan set, and this epic's own corpus — and its `candidate_kind: corpus_spec` rows
include specs whose queue row is `shipped`, `landed` or `superseded`, with no status filter anywhere in
the comparison.

Measured in this epic: staging PLAN-14 produced 12 overlap rows naming it, PLAN-16 produced 11, PLAN-17
produced 14. **Every one was against a shipped spec of this epic or a spec in a CLOSED, ARCHIVED epic**
(`deployment-and-refresh-gaps`, `deployment-configurability`, `lessons-handling-26-08-31-01`). Nothing
was in flight — the epic had zero `running` rows at each of those moments.

By the rule as written, all three candidates were non-disjoint and none was emittable. I emitted them
anyway, recording the reasoning in the decision log each time: overlapping with a plan that has already
shipped is not a concurrency collision, and the standard's own justification for the gate is
concurrency (*"two plans may run concurrently exactly when their touched surfaces do not overlap"*).

## Why it matters

- The gate's error grows monotonically with epic age. An epic's shipped corpus only ever accumulates, so
  every later candidate overlaps more terminal specs than the last. A long-running epic eventually cannot
  emit anything by the literal rule.
- The failure mode is **a false RED**, and it is resolved today only by an orchestrator deciding to
  override the rule it was told is a strict `iff`. That is exactly the escape-hatch shape
  `lessons-handling-26-09-04-01-012` reported for review bots: an override used routinely stops being
  visible as an override.
- A sibling epic that is `closed` (and archived) can hold no live plan by construction, so those rows
  can never represent a real collision either.

## Candidate direction

- Filter the `corpus_spec` candidate population by queue status: compare against rows that can still
  run (`staged`, `launched`, `running`, `parked`), never against `shipped` / `landed` / `superseded`.
  Same for sibling epics: skip an epic whose `phase` is `closed`.
- Whichever way it is fixed, keep the ADR-019 separation — a filtered-out candidate is *not comparable*
  rather than *compared and clean*, so the payload should say how many candidates were excluded by
  status and why, not silently shrink the population.
- Either fix the rule in `orchestrate.md` to match, or fix the verb — but not one without the other:
  today a reader following the doc exactly gets a different answer than one following its stated purpose.
