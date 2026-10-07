envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:51:41Z

component=plan-marshall:phase-3-outline
category=improvement

# An operator-directed scope change updates the outline and strands request.md

Source: Q-Gate finding 099eb2 (3-outline, resolution=taken_into_account).

request.md's clarified_request stated "Scope - ten deliverables" and enumerated D1-D10
including a diff-modules item. The outline carried ELEVEN: it deferred the diff-modules
deliverable entirely, and added two (manage-status plan read for a sibling-worktree
plan; the merge FIFO admission queue read verb) that map to no request requirement.

The outline handled the change well — it named the change as operator-directed and
recorded the deferral with the evidence that must travel with it. The gap is that
request.md was never reconciled, and request.md is the document phase-4-plan reads for
task-planning context.

## Solution

When an operator decision moves scope after refine, reconcile request.md in the same
move (manage-plan-documents request path + request mark-clarified), or the next phase
reads a superseded scope with no pointer to the decision that superseded it.

## Impact

Caught after phase-4-plan had already run, so the remedy's purpose had expired.
