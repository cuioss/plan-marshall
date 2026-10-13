envelope_version=1
sender_type=plan
sender_id=plan-lb-38-review-gate-and-empty-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T23:06:25Z

component=plan-marshall:automatic-review
category=bug

# Do not credit CodeRabbit participation from an edited pre-existing issue comment

## Context

On PR #1752 (head 82b12873) the first automatic-review pass found CodeRabbit absent and looped back. On the second pass, after the @coderabbitai full review trigger, CodeRabbit was credited participated_but_empty through an issue comment, while count_fetched stayed at 6 on both fetches and no new review object or inline thread appeared. The leaf reported that the credited comment was probably CodeRabbit's earlier skip notice, edited, and that the workflow has no step to read what the edited comment says. The review-retrospective step then graded the PR indeterminate: no reviewer produced content.

## Root cause

Participation is credited from the presence of a bot-authored issue comment in the cycle, and an in-place edit of an older comment is accepted as that evidence without checking that the edited body is a finished review of the head (the verdict marker this same plan added to the re-review matcher in D2 is not applied on the participation path).

## Proposed action

Apply the bot's completion evidence (verdict marker, head SHA, or a review object after the trigger) to participation credit as well as to the re-review match, so an edited skip or in-progress notice leaves the bot absent; and surface the credited comment's classification in the automatic-review return so a participated_but_empty credit is inspectable.

## Evidence

- aspect: chat_history_analysis - automatic-review leaf: credit "only through an existing issue comment", "probably the earlier skip-notice comment, edited", not inspected
- status.json: automatic-review prior_firings loop_back, then done "2 empty, 1 refused-structural"
- status.json: project:finalize-step-review-retrospective "indeterminate - 0 findings and no reviewer produced content"
- aspect: plan_efficiency - automatic-review loop-back re-ran finalize steps inside a 3.79M-token finalize
