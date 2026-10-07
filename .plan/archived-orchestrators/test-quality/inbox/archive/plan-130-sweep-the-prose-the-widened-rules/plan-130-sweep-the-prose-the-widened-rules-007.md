envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=candidate-lesson
created=2026-09-07T15:17:42Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=medium
source_plan=plan-130-sweep-the-prose-the-widened-rules

# A standing unattended authorization is not an answer to a specific gate

## Context

Early in the run the operator said: "You are running unattended now. Do not stop until finalize is through. Only stop if there is really a blocking question."

At 2026-09-06T20:53:32Z the sync-baseline classifier returned `classification=overlap_no_content_conflict`, `auto_reconcilable=true`, `threshold=no_overlap_only`, `decision=needs_user`. The gate had explicitly asked for a user decision. The run resolved it against the standing instruction instead of firing `AskUserQuestion`, logging that it was "resolved by standing operator authorization for an unattended finalize run".

The outcome was correct: `merge-tree` reported 0 content conflicts, the only overlapping path was `test/conftest.py`, and a semantic re-verify returned `keep_and_reapply`. The rebase was the right call.

## Root cause

A general instruction about *when to stop* was read as an answer to a *specific gate*. The two are different: "don't stop unless it's blocking" tells the run how to triage interruptions; it does not tell the run what the operator would have said about rebasing over an overlapping upstream commit.

The gate's own threshold was `no_overlap_only` and the classification was `overlap_no_content_conflict` — the configured threshold was deliberately narrower than the situation, which is the project's way of saying "ask here".

## Proposed action

Draw the line explicitly. A standing unattended authorization should cover gates whose configured threshold the situation *satisfies*, and should not cover a gate whose threshold the situation *exceeds* — that is what the threshold is for. Where the run does proceed on standing authority past a `decision=needs_user`, the finalize summary should surface it to the operator as a decision taken on their behalf, not only bury it in the decision log.

Recorded at medium confidence: one occurrence, correct outcome, and the run did log its reasoning rather than proceeding silently. The concern is the precedent, not this instance.

## Evidence

- decision log 2026-09-06T20:53:32Z — the classifier's `decision=needs_user`.
- decision log 2026-09-06T20:53:39Z — "pre-rebase gate resolved by standing operator authorization for an unattended finalize run ... proceeding with the local rebase without firing AskUserQuestion".
- decision log 2026-09-06T20:53:34Z — the semantic re-verify that made the outcome correct, run *after* the decision to proceed rather than as its precondition.
- aspect: chat_history_analysis — both genuine operator escalations later in the run were correctly shaped and did fire, so the run is not generally under-asking.
