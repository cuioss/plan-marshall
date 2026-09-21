envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=candidate-lesson
created=2026-09-13T08:20:16Z

component=plan-marshall:automatic-review
category=bug

# pr wait-for-comments samples each bot's newest comment, so an in-place refusal edit is invisible

Carry-forward from plan `the-foreign-gate-population-and-branch-f-recovery` (finding
`658eec`, resolution `accepted`). **Still live on main** — deliberately not fixed in
PR #1473.

## Mechanism

Observed on PR #1473 at head `3aee443ae` (iteration 8). CodeRabbit's auto-review fired 18
seconds after the push and REFUSED on quota, delivering that refusal as an in-place EDIT of
its persistent walkthrough comment (`IC_kwDOQ3xasM8AAAABUHvnOw`, updated `22:56:59Z`).

`pr wait-for-comments` reported `rate_limited_bots[]` naming only `sourcery` — CodeRabbit
absent — and an empty `movement_matched_bots[]`. The detector samples each bot's NEWEST
comment (here its `22:38:15Z` "Action performed" reply) rather than the edited walkthrough,
so an in-place edit that is older by CREATION time but newer by UPDATE time is never
inspected. `movement_matched_bots` does not cover the gap either, because coderabbit
declares `participation_requires_update: false`.

Only reading comment BODIES surfaced the refusal.

## Why it matters

A caller trusting `rate_limited_bots[]` concludes no bot was rate-limited and proceeds as if
CodeRabbit had simply not answered yet — which selects the WRONG recovery
(wait-for-silence instead of wait-for-window). On a quota-limited reviewer those two
recoveries differ by roughly an hour of wall clock each time they are confused.

## Pairing

Fix together with the sibling candidate for finding `852b0f` (the fresh-edit currency arm
crediting a thread acknowledgement as a review). Same root assumption: these bots publish by
EDITING a persistent comment, while both detectors assume publication means a new or newest
comment.

## Why it was not fixed in-run

Same rationale as `852b0f`: observed after the operator-directed pipeline-fix round had
landed, and fixing it would have advanced HEAD and restarted the mandatory-review cycle that
had already cost three ~90-minute quota waits. Containment: every refusal this run was
ultimately detected by reading comment bodies, the documented compensating practice, so no
recovery was actually mis-chosen.

File: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
