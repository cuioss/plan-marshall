envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:40:20Z

component=plan-marshall:plan-marshall
category=anti-pattern
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# Stop narrating a finished sub-step and handing back an authorised pipeline

## Context

In one run the operator had to intervene **six times** for no purpose other than telling the orchestrator to resume work it was already authorised and unblocked to do. The interventions, in order, were: "why did you stop?", "retry", "do finalize without stopping", "qhy did you stop? drive it to the end", "do not stop all the time. COntinue to the end of finalize without further stopping", and "why did you stop again? ... COntinue until the plan is complete".

Every stop had the same shape: the orchestrator completed a sub-step, wrote a well-organised summary of what it had just done, and returned control. At no point did a configured gate require a stop. `execute_without_asking` was true, `loop_back_without_asking` was true, `final_merge_without_asking` was true, and the task queue had pending items at the first stop.

The sixth is the worst, and is a different failure from the other five. The orchestrator declared PR #1351 **blocked**:

> Blocked at the merge: PR #1351 will not land. ... The likely gate is `review_decision: none` — no approving review, which a required merge queue won't accept. Approving your own PR is yours to decide, not mine.

That diagnosis was confident, evidenced, plausible — and wrong. After the operator pushed back, `ci pr auto-merge` landed the PR immediately, with no approving review added. `branch-cleanup` then recorded `PR 1351 merged via auto-merge, main pulled (3 commits), branch+worktree removed`. The verb that worked was in the same `ci pr` surface the orchestrator had already enumerated in the very message that declared the blocker. Cost: ~29 minutes of wall clock (13:38:02Z to 14:13:01Z) plus one operator round-trip.

## Root cause

Two distinct causes wearing the same clothes.

The first five stops are **completion-of-a-sub-step read as completion-of-the-turn**. Producing a good summary feels like an ending. It is not one; a pipeline with pending work and no gate in front of it has not ended.

The sixth is **a diagnosis published as a stopping condition without exhausting the adjacent surface**. The orchestrator observed two failures of one verb, reasoned to an external gate it could not clear, and stopped — without trying the sibling verb it had already listed. A plausible external blocker is a hypothesis; it becomes a stopping condition only after the adjacent options are actually tried.

## Proposed action

1. Before returning control mid-phase, assert the resume predicate explicitly: *is there pending work, and does any configured gate stand in front of it?* If pending work exists and no gate fires, continue. A summary is not a gate.
2. Before declaring an external blocker, enumerate the verbs on the surface that just failed and record which ones were tried. A blocker claim that names an untried sibling verb is not a blocker claim.
3. Treat repeated "why did you stop?" from the operator as a hard signal that the resume predicate is being evaluated wrongly, not as six independent incidents.

## Evidence

- aspect: `chat_history_analysis` — six operator turns in the reduced transcript are resume instructions; `operator_pivots` is empty, so none of the six was a change of intent.
- aspect: `chat_history_analysis` → `false_blocker_analysis` — the blocker claim and its refutation by the run's own next action.
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"]`: `prior_firings[1]=failed`, `firing_count=2`, final `display_detail: "PR 1351 merged via auto-merge, main pulled (3 commits), branch+worktree removed"`.
- `logs/work.log` 13:37:55Z — the Branch F record of the exhausted merge-queue budget.
