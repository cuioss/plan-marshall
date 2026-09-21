envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:00:39Z

# branch-cleanup is orchestrator-shaped but dispatched as a leaf

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source_plan: plan-truth-103
source_aspects: chat_history_analysis, execution_context_dispatch_audit

## Context

`default:branch-cleanup` was dispatched as an `execution-context` leaf on this
run and needed three separate workarounds to complete, each because the step's
documented procedure requires a capability a dispatched leaf does not have:

1. Its landing poll is paced with a `sleep` the harness blocks.
2. Its documented `until`-loop is forbidden by this project's own hard rules
   (no shell loops, one command per Bash call).
3. It fires `AskUserQuestion` gates that a dispatched leaf structurally cannot
   reach — operator input is unreachable inside a dispatched envelope.

The run worked around all three without affecting any verdict, and the dispatch
itself reported the mismatch. The step did land correctly, and notably it
declined to record a terminal `done` when worktree removal was blocked
(`plan_dir_not_moved_back`), reporting `cleanup_owed: true` and leaving the
record absent so the resumable re-entry check would fire — a step correctly
refusing to claim a completion it had not achieved.

## Root cause

The step's authoritative doc describes an orchestrator-tier procedure (blocking
waits, interactive gates) while the manifest dispatches it at leaf tier. The
leaf/dispatch-topology contract in `ref-workflow-architecture/standards/agents.md`
is explicit that a leaf cannot fire `AskUserQuestion` and must instead return a
prompt-required envelope; `branch-cleanup` does not do that, it simply documents
the gate.

## Proposed action

Reconcile the declared tier with what the step requires. Either:

- move `branch-cleanup` to orchestrator tier (it is already the step that owns
  the merge, the queue wait and the merge-authorization gates — all of which are
  orchestrator concerns), or
- rewrite its procedure for leaf execution: replace the `sleep`-paced poll with
  a single synchronous bounded call, and convert every `AskUserQuestion` gate
  into a documented prompt-required return envelope.

The first is the smaller change and matches what the step actually is.

## Evidence

- aspect: chat_history_analysis — the merge dispatch reported: "its landing poll is paced with a `sleep` the harness blocks, its documented `until`-loop is forbidden by the project's own hard rules, and it fires `AskUserQuestion` gates a leaf cannot reach. It worked around all three without affecting any verdict, but the step reads as designed to run inline in the orchestrator."
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].facts`: `merge_mechanism: merge_queue`, `merge_state: merged`, `cleanup_owed: "false"`, `work_performed: "true"`
- contract: `ref-workflow-architecture/standards/agents.md` § "Leaf cannot fire AskUserQuestion — return a prompt-required envelope"
