envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:27:50Z

## Finding: `manage-tasks` finalize-step auto-promotes a `module_testing` task to `done` BEFORE its verification gate runs

**Observed in**: main, reproduced **4 times** across `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.

### What was observed

`manage-tasks`' finalize-step handling marks a `module_testing` task `done` at the **step
level**, and that promotion fires **before** the task's verification gate has run. The task
therefore reaches `done` on the strength of the step completing, not on the strength of the
gate passing.

Reproduced 4 separate times in this one plan.

### Why it matters — this defect is self-concealing

This is not merely an ordering bug; it is an ordering bug that **destroys its own
evidence**. The auto-mark is precisely the mechanism that would let a dispatched leaf hand
back a green result with **no gate behind it**: the task reads `done`, the step reads
complete, and nothing in the recorded state distinguishes "the gate ran and passed" from
"the gate never ran". Any audit performed after the fact sees only the green.

That self-concealing property is what makes it worth a dedicated plan rather than an
opportunistic fix — the population of runs that have already been affected cannot be
recovered from the persisted state, so the fix must be paired with a detector that can
tell gated-green from ungated-green going forward.

### Suggested shape of a fix (not implemented)

- Make the `done` promotion **consume the gate's outcome** rather than the step's
  completion — a task must not be promotable without a gate verdict in hand.
- Record the gate verdict as a first-class field on the task so ungated-green is
  representable and detectable, instead of being indistinguishable from gated-green.
- Sweep for other profiles (not just `module_testing`) that take the same step-level
  auto-promotion path; the observed count of 4 is a **floor**, not an enumeration.
