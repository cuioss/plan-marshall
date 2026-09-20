envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:51:32Z

component=plan-marshall:workflow-integration-git
category=improvement

# A baseline-reconcile conflict can be proximity, not semantics — and the difference decides the rebase

Source: Q-Gate finding 69d10b (2-refine, resolution=taken_into_account).

Three-way merge reported a conflict in manage-locks/SKILL.md. Reading both sides showed
upstream PR #1479 extended the same log_lock_event WARNING-level bullet (adding
cap-disagreement) that this plan's D5 corrects (path description .plan/logs/ ->
<main>/.plan/local/logs/). The edits target one paragraph but are additive and
non-overlapping in intent.

## Solution

Baseline-reconcile findings must record, per conflicted file, whether the conflict is
SEMANTIC (the two sides disagree about behaviour) or PROXIMITY (git's adjacent-hunk
context matching over disjoint intents). The remedy differs: a proximity conflict is
resolved by unioning both edits verbatim at rebase time; picking either side silently
drops a landed upstream change.

## Impact

Every plan that survives long enough to absorb upstream drift.
