envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:01:58Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Fit the PR Intent draft to the renderer limit so Non-goals are never cut

## Context

On plan lb-23-verify-builds the create-pr step rendered an Intent section whose Non-goals paragraph was cut entirely: the PR body showed an empty "Non-goals." heading followed by the truncation marker (1363 of 1500 characters written, 605 of 1867 draft characters not shown). Reviewers therefore could not see the six scoped-out items. The step logged the truncation and did not re-render, because the workflow documents only logging.

## Root cause

The draft is written without knowing the renderer's 1500-character limit, and truncation cuts from the end, where Non-goals sit. Non-goals are the part of the Intent that keeps a review bot from reporting deliberate omissions as gaps, so they are the worst part to lose.

## Proposed action

- State the limit in the create-pr workflow and have the draft author fit it, or have the renderer return `intent_truncated: true` as a refusal the step must answer by shortening and re-rendering once.
- If truncation must remain possible, order the Intent so Non-goals render before the approach narrative, or give Non-goals their own budget.

## Evidence

- aspect: chat_history_analysis - create-pr hand-back: `intent_truncated: true`; "the whole non-goals paragraph was cut ... I did not re-render, because the workflow documents only logging on truncation".
- Review outcome: none of the 7 actionable CodeRabbit comments asked for a non-goal, so the truncation cost nothing measurable on this PR; the triage leaf checked ("none of the six asks for anything on the plan's non-goals list").
