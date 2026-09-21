envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T14:41:36Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# finalize-step-simplify is classified DISPATCHED but its Step 3 requires a second dispatch

`default:finalize-step-simplify` is listed under `## Dispatched steps` in
`phase-6-finalize/standards/dispatch-inline-split.md`, so the dispatcher runs it
inside an `execution-context` envelope. Its own workflow body
(`phase-6-finalize/standards/finalize-step-simplify.md`) Step 3 instructs the
step to issue a **second** `Task:` dispatch — the isolated cognitive-review
sub-agent.

A dispatched leaf cannot spawn a further subagent (the leaf/dispatch-topology
invariant in `ref-workflow-architecture/standards/agents.md`), so the leaf
correctly refused and returned:

```toon
status: blocked
error: leaf_cannot_dispatch
```

The step could not complete inside its own envelope. The orchestrator had to run
the inner cognitive-review dispatch itself from main context and mark the step
done by hand.

## Why this is a real contract violation

This is not a runtime hiccup — it is a **two-level-dispatch contract violation in
the step's own definition**. The classification (DISPATCHED) and the body's
required control flow (issue a `Task:`) are mutually unsatisfiable. Every run of
this step on this path either blocks or is completed by an out-of-band
orchestrator repair, which means the step's `done` record does not describe an
envelope-native completion.

## Corrective action — pick one, do not leave both halves as-is

1. **Reclassify the step INLINE.** Move `default:finalize-step-simplify` to the
   `## Inline steps` roster in `dispatch-inline-split.md`, so its Step 3 dispatch
   originates legally from main context. This is exactly the shape
   `project:finalize-step-lessons-housekeeping` already uses — an inline wrapper
   whose body is allowed to dispatch.

2. **Or fold Step 3 into the single envelope.** Keep the DISPATCHED
   classification and remove the inner dispatch: the cognitive review runs as an
   in-context skill load inside the one envelope (in-context `Skill:` loading is
   not subagent dispatch and is permitted for a leaf).

## Generalisable rule

Any step classified DISPATCHED must have a body that is executable by a leaf: no
`Task:` dispatch anywhere in its control flow. A sweep of the dispatched roster
for bodies containing a `Task:` directive would surface any sibling instances of
this same violation.
