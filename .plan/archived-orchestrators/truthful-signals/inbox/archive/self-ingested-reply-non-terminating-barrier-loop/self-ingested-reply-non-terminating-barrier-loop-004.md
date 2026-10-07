envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:45:07Z

component=plan-marshall:phase-4-plan
category=anti-pattern
bundle=plan-marshall

# A task's depends_on ordering can make its own success criteria structurally unsatisfiable

## Observation

PLAN-111's success criteria required each new regression test to be "observed FAILING pre-fix" — a standard TDD-style acceptance check. But the plan's own `depends_on` graph ordered the fix task **before** the test tasks, so by the time any test task ran, the fix was already in place. There was no point in the task graph at which "observed failing pre-fix" could actually be observed; the criterion and the ordering contradict each other by construction.

This is a purely structural argument — no test was skipped and no false claim was made, but the acceptance check as written could never have been satisfied regardless of execution care.

## Why it matters

A success criterion that references a temporal relationship ("before the fix", "pre-fix", "prior to X landing") is only checkable if the task graph actually produces a state where that relationship holds. Writing the criterion without checking it against `depends_on` ordering produces an acceptance check that looks rigorous but is vacuous — the same "vacuous guard" archetype already recurring across this epic's history, applied to plan-authoring rather than to code.

## Corrective rule

When a task's success criteria describe a before/after or pre/post-fix observation, verify at plan-authoring time (phase-4-plan) that the `depends_on` graph actually schedules a task run in the "before" state. If the fix task's dependents cannot run before the fix without redundant duplication, either reorder the graph (test-task depends only on setup, not on the fix) or rewrite the criterion to something the graph can actually produce (e.g., "the fix commit's diff is reviewed to confirm test failure would have occurred", or an inline pre-fix assertion baked into the test task itself).

## Status

Structural finding only — no corrective change made in this plan; carried to the epic for cross-plan pattern tracking.
