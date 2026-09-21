envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T13:34:21Z

component=plan-marshall:persona-plan-orchestrator
category=anti-pattern

Relayed from Token-Sheriff PLAN-08 (`standalone-guards`, PR #730 / `c40963ac`). ⛔ **The defective count was the ORCHESTRATOR'S**, in the spec it wrote: the acceptance criterion asserted a number that the spec's own per-file breakdown contradicted, and the plan recounted and corrected it (twelve real package-pattern occurrences, not ten; the 23 harmless prose ellipses were correctly left alone — 12 + 23 = 35, which matches the orchestrator's own occurrence count, so the breakdown was right and the headline was wrong). Relayed against the orchestrator persona rather than a script, because no tool produced the error.

# Candidate lesson: acceptance criterion carried a count that its own per-file breakdown contradicted

**Origin signal**: Q-Gate finding, phase `4-plan`, resolution `fixed`.
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).

## Observation

The solution outline stated an acceptance criterion in prose ("ten glyph occurrences")
while the per-file breakdown immediately beneath it summed to twelve. A recount at
Q-Gate time confirmed twelve was correct, so the prose count — not the breakdown —
was the stale half.

The two halves are the same fact written twice: a total, and the addends that produce
it. Nothing in the authoring path re-adds the breakdown and compares it to the stated
total, so the disagreement survived into the plan and was only caught because the
Q-Gate pass happened to recount.

## Why it is candidate-lesson shaped

This is the count-prose-staleness class applied to acceptance criteria rather than to
documentation: a criterion is a gate, so a wrong total makes the gate assert the wrong
thing. A verification step that "passes" against the stated ten while twelve exist is a
green result over an under-counted surface.

Possible corrective (for the orchestrator to judge): when an acceptance criterion states
a count AND the same deliverable enumerates the addends, the count must be derived from
the enumeration at authoring time, and re-derived whenever either side is edited.

## Cross-plan judgement deferred

Whether this generalises beyond this plan — and whether it belongs to the epic, to the
global corpus, or to an existing lesson on count-prose staleness — is the orchestrator's
call. This plan transmits the candidate only.
