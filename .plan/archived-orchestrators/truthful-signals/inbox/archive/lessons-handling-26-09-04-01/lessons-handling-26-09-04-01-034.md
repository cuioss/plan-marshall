envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:29Z

component=plan-marshall:phase-4-plan
category=bug

# TDD-first task description contradicts the depends_on ordering the queue enforces

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-07-21-002` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-07-21-002`, created 2026-09-07, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Observed

Plan `carry-refresh-token-through-code-exchange` (TokenSheriff) carried an
explicit operator directive: tests must be authored and **observed failing on
the missing value** before the production change lands.

Phase-4-plan derived two tasks from the single deliverable:

- TASK-1 — implementation (production change)
- TASK-2 — module_testing, `depends_on: [TASK-1]`, whose description instructed
  the executor to author the tests and observe them failing *before* the
  production change

These two cannot both hold. The queue runs `depends_on` order, so TASK-1 lands
the production change first and the tests can never be observed red. The
executor correctly followed the dependency graph and reported the gap rather
than claiming a red phase it never obtained — but the plan as derived made the
operator's mandatory directive unsatisfiable.

## Why it matters

The red observation is what proves a test detects the defect rather than
passing vacuously. Silently dropping it yields a green suite that says nothing
about whether the assertions bind — precisely the \"confident signal hides a
caveat\" failure the plan existed to prevent. Worse, a less careful executor
would have reported \"TDD followed\" because the tests exist and pass.

## Directive

When a deliverable carries a TDD ordering constraint, phase-4-plan MUST derive a
task graph that can express it. Pick one:

1. **Invert the dependency** — a test-authoring task with no `depends_on`, whose
   completion criterion is an observed assertion failure, and an implementation
   task depending on it. Requires the tests to compile against the not-yet-added
   API, so this only works when the change is additive at call sites.
2. **Single task, ordered steps** — one task whose steps are red → green →
   refactor, so ordering is intra-task and the dependency graph is not asked to
   carry it.

Do NOT emit a description whose prose ordering contradicts the task's own
`depends_on`. If the graph cannot express the constraint, say so at plan time
rather than leaving the executor to discover the contradiction at run time.

## Note on retroactive recovery

The orchestrator recovered the evidence after the fact by reverting only the
population site (keeping the accessor, so the tests still compiled) and
re-running: the tests failed with `expected: <…> but was: <null>` — an assertion
failure on the missing value, not a compile error. This is a valid demonstration
and is worth codifying as the fallback when the ordering was already lost, but
it is a repair, not a substitute for deriving the graph correctly.
