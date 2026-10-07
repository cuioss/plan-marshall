envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:24:35Z

## The execution-context level ladder is an unmeasured cost lever

Source: same Day 1 whitepaper (see message 001 for provenance and the outside-document caveat).

### The observation

The paper names model routing as a first-class OpEx lever: reserve frontier models for requirements,
architecture and initial implementation, and route deterministic lower-complexity work — it names test
generation, code review, and CI/CD monitoring — to smaller, faster, cheaper models.

plan-marshall already owns the mechanism. `execution-context-level-1` through `-7` pin model and effort
per dispatch, and every `Task:` invocation in the corpus selects one. What is absent is any evidence that
the selections are cost-derived. A level written into a workflow doc a year ago and copied forward since
is indistinguishable, from the outside, from one chosen on measurement.

### The candidate work

Derive the level assignment population from the corpus rather than asserting it: enumerate every
`execution-context-level-N` dispatch site, join to what that step actually does, and report the
distribution. Then the question becomes answerable — which dispatches are pinned above the tier their
work needs, and what does the gap cost per run.

Two constraints make this narrower than it sounds:

- The output must publish its population size, per the epic's own discipline. A survey that finds "no
  over-pinned dispatches" from an enumeration that silently missed half the sites is the archetype.
- Re-pinning a level is a behavioural change to a runtime step, so it is downstream of WS-01 having
  something that can tell a level-4 result from a level-2 one. Measuring the distribution is not.

### Relation to the epic

Sits against the third done-condition — a readable price — but on the **execution** side rather than the
instruction-carrying side. The orchestrator may judge it closer to `code-intelligence-substrate` than to
this epic; filed here because the ladder is part of the harness this epic is chartered to measure, and
routed at the orchestrator's discretion.

### Status

Directional. The paper asserts the lever and supplies no data; our own distribution is unmeasured, so
nothing here estimates a saving.
