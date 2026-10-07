envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T11:35:41Z

## Proposed lesson metadata

- `component`: `plan-marshall:manage-execution-manifest`
- `category`: `anti-pattern`
- `title`: A hypothesised count of predicates is a sample — derive the population before scoping

## Observation

The request for `compose-time-subtractions-drop-steps` hypothesised **3**
compose-time subtraction predicates. Deriving the population mechanically from
the `_decide` matrix produced **13**. Five rows subtracted steps entirely
silently — no decision-log line and no compose-result record — and two of those
collapsed `phase_6.steps` to a three-step minimum with no per-drop record.

Had the plan been scoped to the hypothesised three, ten subtraction sites would
have kept silently dropping steps while the plan reported the class as closed.

## Why this recurs

This is the same archetype the corpus already carries under other names: a
reviewer's list of call sites is a sample, not an enumeration; "250 candidates
examined" is a volume, not a coverage number. The new instance adds the *request
narrative itself* as a source of false enumerations. A count that arrives in the
request is a hypothesis authored without access to the population.

## Rule

When a request names a count of sites, predicates, or call sites, treat the
number as a **lower bound and a hypothesis**. Before scoping, derive the
population mechanically from the structure that generates it (here: the `_decide`
matrix rows), and scope to the derived population. If the derived count differs
from the hypothesised count, say so explicitly in the outline — the delta is a
finding in its own right, not a silent scope adjustment.

Corollary: every detector that guards a set must be **population-derived** from
the same structure, not written against the enumerated examples. An enumerated
detector passes green the moment the population grows.
