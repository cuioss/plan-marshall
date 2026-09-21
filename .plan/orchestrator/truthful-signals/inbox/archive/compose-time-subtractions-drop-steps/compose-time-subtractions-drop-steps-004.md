envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T11:35:58Z

## Proposed lesson metadata

- `component`: `plan-marshall:phase-3-outline`
- `category`: `anti-pattern`
- `title`: Widening readers without shipping a writer builds a guard whose predicate can never fire

## Observation

Defect A in this plan was initially scoped by the outline as "widen the two
readers so they honour the new immunity path". A third component was nearly
omitted: nothing in the scope **wrote** the immunity marker the widened readers
would read.

Shipping only the readers would have produced a structurally unreachable path —
a guard whose predicate can never evaluate true, in a diff that looks complete
and passes every test written against it, because no test can construct the
input that would exercise it.

## Why this recurs

This is the **vacuous-guard archetype** the project keeps hitting (already at
n≥4 in the corpus, including one instance introduced *by a fix for* the
archetype). The new detection heuristic this run contributes is the
reader/writer asymmetry:

> Any change that teaches a reader to recognise a new state must be checked for
> the presence of a **producer** of that state, inside the same scope.

## Rule

When an outline's deliverables are all on the **consuming** side of a new signal
(readers, guards, filters, validators, branches keyed on a new flag/marker/field),
stop and ask the completing question: *what writes this?* If no deliverable
produces the state, the outline is incomplete — the missing writer is a
deliverable, not a follow-up.

The check is cheap and mechanical: for each new predicate, name the concrete call
site that sets its input to the true-branch value. If that call site is not in
the diff and not already in main, the guard is vacuous.
