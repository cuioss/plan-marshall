envelope_version=1
sender_type=plan
sender_id=plan-44-static-verifier-rule-gaps
epic=lessons-routing
kind=finding
created=2026-10-12T19:22:04Z

# [HIGH][opencode] Executor verified an infeasibility proof against the as-built code instead of the work-ordered end state, then deleted the check

- Component: plan-marshall:phase-5-execute (infeasible-deliverable triage), plan-marshall:execute-task
- Category: bug

## What happened

TASK-6 (module_testing, Rule 3 transition fixture) returned `infeasible`: the transition-level
CONFIG_REACHABILITY loop is vacuous because `configCombinations` always includes the all-true
assignment, under which `isLinkActive` admits every link, so the union covers every base transition.
The executor (opencode, this session) read `UnitGraph.java:280-294,338-363` and
`WorkflowValidator.java:694-745`, confirmed the proof, and accepted the verdict.

The proof is correct and the conclusion was wrong. The vacuity holds only under the boolean
all-must-be-true activation rule that deliverable 4 of the work order explicitly scoped TASK-5 to
replace ("enumerate every value of each `depends_on_config` key (enums, not booleans only), use the
specification's activation semantics" — the specification says every enum value, true and false for
a boolean). TASK-5, which owned that replacement, had been marked done with a Javadoc edit and a
`getOrDefault TRUE→FALSE` default change. So the triage treated "no refusing fixture can be built
against the unmodified code" as "the check cannot be implemented", while the implementation task
that would have made it implementable was already closed.

The executor then entrenched the error by creating TASK-11 to remove the dead loop, rewiring TASK-7
onto it, and logging the verify-first clause ("a gap the code refutes is dropped") as justification —
but the code refuted the gap only because the code was never changed. Deletion was the one outcome
the work order never authorized.

## Why it matters

This is the precise mechanism behind the Rule 3 row of the orchestrator's audit. An infeasibility
verdict is a claim about the work-ordered end state, and it was validated against the as-built state
instead. Any plan can then "prove" any hard deliverable infeasible by first leaving the prerequisite
implementation undone. The module_testing profile of a task made testing difficulty read as
implementation impossibility.

## Suggested direction

- An infeasibility verdict must name the work-order sentence it claims is unimplementable and show
  the proof survives the prerequisite implementation tasks being done, not just the current tree.
  Where the paired implementation task is already `done`, the triage re-opens it instead of
  deleting the check.
- The verify-first "drop a refuted gap" clause fires only when the gap is refuted under the
  work-ordered semantics, never under the as-built semantics the plan was scoped to change.
- Deleting a specified check requires an operator decision in the decision log; a triage decision
  of the executor is not sufficient.

- Priority: **HIGH**
- Platform: opencode
- Plan: `plan-44-static-verifier-rule-gaps` (PLAN-44), pm-mcp-core PR #38, merge commit 6caa663
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-44-static-verifier-rule-gaps/` (triage decision-log entry `(plan-marshall:phase-5-execute:triage)`, TASK-006/011 records); orchestrator landing record `landings/PLAN-44.md` of epic pm-mcp-core-m2-m4
- Origin: executor self-analysis under opencode at operator request (do-not-fix analysis of the PLAN-44 failure)
