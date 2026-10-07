envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:52Z

# Expose the merge FIFO queue through a verb instead of a hand-read

## Context

During finalize, `integrate_into_main` blocked 23 times reporting `admission=blocked`, `blocking_plan_id=null`, `waiting_count=2`, while `merge_lock check` simultaneously reported `status=free`. Diagnosing that apparent contradiction required opening `merge-queue.json` directly, because `manage-locks` exposes no verb that inspects the admission queue.

The hand-read led to a wrong inference and a destructive action: the front entry was judged to be a dead plan's orphaned slot and pruned. It was a live sibling plan holding the merge mutex. This is recorded in full as Q-Gate finding `8d44fd`.

## Root cause

The queue is real state with no read surface. When the only way to inspect a structure is to open its serialization by hand, the reader must also re-implement its semantics — including holder liveness — and any mistake in that re-implementation becomes actionable against live state.

## Proposed action

Add a read-only `manage-locks merge-queue list` verb returning the ordered entries, each with its holder's liveness resolved through `git-workflow locate-plan-checkout` rather than through a raw plans-directory read. This is the one claim from the earlier finding `9aea7b` that survived: the other two assertions in that finding were refuted, but the missing inspection verb was the enabler.

## Evidence

- Q-Gate finding `8d44fd` (severity error, still pending): "manage-locks exposes no verb to INSPECT the queue, which is what forced a hand-read of merge-queue.json and made a wrong inference actionable"
- 23 consecutive blocked admissions with `blocking_plan_id: null` while `merge_lock check` reported `status=free`
- Immediately after the prune, `merge_lock check` returned `status=held`, `holder_plan_id=participation-credit-anchored-to-merge-candidate`, `staleness=fresh`
