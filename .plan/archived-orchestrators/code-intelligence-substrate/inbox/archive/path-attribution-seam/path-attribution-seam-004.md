envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T18:33:12Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# A review comment that drove a code fix was recorded as `0 comment(s) found` and counted as `0 actionable` — two independent signals under-reported the same true positive

## What happened

On PLAN-CIS-023 (PR #1072), `pr-agent` (posting as `cuioss-review-bot`) filed a substantive review comment identifying a real defect: `merge_path_claims` iterated an implementor's claims collection outside its guarding `try`, so a truthy non-iterable return blanked the whole ownership map. The finding was confirmed, accepted, and fixed on-branch as TASK-012.

Two finalize signals recorded that same comment as absent or inert:

| Signal | Recorded value |
|--------|----------------|
| `automatic-review` step `display_detail` | `0 comment(s) found (unified triage pending)` |
| `project:finalize-step-review-retrospective` `display_detail` | `1 reviewer compared, 1 true-positive comment (0 counted actionable)` |

Meanwhile `manage-findings` holds the comment as a `pr-comment` finding with `resolution: fixed` and a resolution detail describing the accepted defect and its remedy.

Both recorded signals are internally coherent and neither reads as broken. A reader scanning the finalize output sees a clean automated-review pass and a retrospective reporting zero actionable comments, and would reasonably conclude the bots found nothing worth acting on. The opposite is true: the single comment the bot filed was a true positive that changed production code.

## The two distinct defects

These are **not** one defect seen twice — they fail for different reasons and need separate fixes.

1. **`automatic-review` reported `0 comment(s) found`.** The step ran at `head_at_completion: 9f17cafa5` and observed an empty comment set. The bot's comment landed on a later poll. This is the *review-outruns-the-gate* shape: the step's count is a point-in-time reading being rendered as a completed census. The `display_detail` states a bare count with no as-of qualifier, so nothing in the rendered line signals that the reading could still move.

2. **The retrospective counted `1 true-positive comment (0 counted actionable)`.** Here the comment *was* seen and *was* classified a true positive, yet the actionable counter stayed at zero. A comment that produced a code fix in the same run is the strongest possible evidence of actionability. Whatever predicate gates the `actionable` bucket did not fire on a comment whose remediation is recorded in the very same findings store the retrospective can read.

## The rule

**Do X:** Derive an "actionable" count from the finding's *outcome* — a `pr-comment` finding that reached `resolution: fixed` in this run is actionable by construction, and the retrospective should reconcile its counter against `manage-findings list --type pr-comment --resolution fixed` rather than against its own independent classification pass.

**Do X:** When a step's count is a point-in-time poll that a later event can invalidate, say so in the `display_detail` (as-of qualifier or explicit pending marker). `0 comment(s) found (unified triage pending)` already carries a *pending* hint, but the leading `0` is what a reader takes away.

**Not Y:** Do not read a zero-count review signal as evidence that reviewers found nothing. Per the standing rule, only `ci pr comments --pr-number N` is evidence of participation, and a green finalize is never proof the bots saw the diff.

## Why this belongs in front of a human

The mechanical consequence is small — the fix shipped either way, because the finding *was* correctly stored and triaged through `manage-findings`. The consequence that matters is to the epic's measurement arm: if `0 counted actionable` accumulates across plans, the review-effectiveness metric will trend toward "the bots contribute nothing" using data that contains the counter-example.

## Routing note

This is a review/PR-apparatus signal, not a code-intelligence one. Per the three-way finding-routing rule it most likely belongs to the `review-apparatus` epic rather than `code-intelligence-substrate`. Emitting it here unclassified per the orchestrated-plan contract — the plan performs no global-vs-epic classification, so this is flagged for the orchestrator to re-route via the INBOX rather than acted on locally.
