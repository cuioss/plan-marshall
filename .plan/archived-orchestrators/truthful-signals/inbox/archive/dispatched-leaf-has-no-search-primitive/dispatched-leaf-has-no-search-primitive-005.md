envelope_version=1
sender_type=plan
sender_id=dispatched-leaf-has-no-search-primitive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:19:59Z

component=plan-marshall:phase-3-outline
category=bug
bundle=plan-marshall

# phase-3-outline prescribes a Task: dispatch for the change-type LLM fallback, which a dispatched leaf cannot perform

## Observation

`phase-3-outline` documents a `Task:` dispatch as the fallback path when the deterministic change-type heuristic returns `ambiguous`. But `phase-3-outline` itself normally runs **inside a dispatched `execution-context` leaf**, and a leaf cannot spawn a further subagent — that is the standing leaf/dispatch-topology invariant in `ref-workflow-architecture/standards/agents.md`.

So the prescribed fallback is unexecutable from the executor the workflow actually runs in. Following the workflow verbatim means violating the leaf invariant; obeying the invariant means the documented step has no path.

## Same archetype as the plan's own target defect

This is structurally identical to the permission-asymmetry defect PR #1046 fixed: **a workflow step prescribes a capability that the executor class running it does not hold.** The two instances differ only in which capability is missing (`Grep` vs. subagent dispatch).

That makes it a *class*, not two incidents. Worth a population-derived sweep: enumerate every workflow step reachable from a dispatched leaf that prescribes `Task:`, `AskUserQuestion`, `Grep`, or `Glob`, and check each against the leaf's actual runtime tool grant. Do not spot-check — the recurring project failure is treating a reviewer's or an author's sample of call sites as an enumeration.

## Corrective rule

Every workflow step must be executable by the executor class that the workflow is dispatched into. When a step needs a capability only the main-context orchestrator holds, the step must return a structured signal to the orchestrator (the sanctioned pattern already documented for `AskUserQuestion` as the "prompt-required envelope"), not prescribe the unreachable call directly.

## Status

**NOT FIXED** — out of scope for PR #1046, carried to the epic.
