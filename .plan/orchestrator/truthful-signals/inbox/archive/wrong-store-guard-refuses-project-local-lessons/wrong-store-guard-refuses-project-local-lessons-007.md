envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:57:44Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-07-29

# phase-5-execute Step 2.5 tells the DISPATCHED leaf to pin its own cwd, which a leaf cannot do

`phase-5-execute` Step 2.5 instructs the dispatched leaf agent to pin its own working directory to the plan's worktree. This is structurally impossible for a leaf: a dispatched agent's cwd resets between Bash calls (per the environment's own contract), so no instruction inside the leaf's envelope can make that pin durable across its own Bash calls. A dispatched agent DOES correctly inherit an already-pinned cwd from its parent when the PARENT pinned it before dispatch — the pin has to happen upstream of the dispatch boundary, not inside it.

## Impact

The fix belongs at the orchestrator/dispatcher layer: pin the cwd (or pass `WORKTREE` and require every git call to route through it, as `execution-context.md` already does for other envelopes) BEFORE issuing the `Task:` dispatch for Step 2.5, and drop the leaf-side self-pin instruction since it can never be satisfied. This plan did not attempt to fix Step 2.5 itself — it surfaces the defect for the epic to action, since fixing it touches phase-5-execute's dispatch step, outside this plan's surgical scope.
