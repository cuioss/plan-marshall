envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:03Z

# Candidate lesson: Stop filing approval-only and gate-status comments as findings

- Component: plan-marshall:workflow-integration-github
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-024 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Retrospective of plan primitive-spi-and-validators (script opportunities, chat history). Counted from the review-read and triage reports in the session and from decision log 318de9.

## Context

Over four review reads of pull request 18 the fetch stored 11 comments that carry nothing to decide: five Sourcery review bodies reading "Sourcery assessment: Approved." (c5fa78, 215a12, 9233cd, 221d69, af9b70), four SonarQube Cloud quality-gate notices (a18151, 63920a, 14d71a, 09e179) and two CodeRabbit review summaries (e46be1, fa1f75). Each became a pending finding. Eight went through the triage hand-off and got a reply on the pull request; the last three were resolved `taken_into_account` by the orchestrator itself, without the triage step and without a reply, because a pending finding blocks the merge barrier and a triage hand-off for three approvals costs more than it decides.

## Root cause

The noise filter of the fetch drops bot chatter but keeps approval bodies, gate notices and review summaries. A gate notice duplicates what the Sonar read already reports; a review summary duplicates its own inline comments. Because every stored comment is a pending finding, each one needs a disposition before merge.

## Evidence

- Review-read reports: stored 8, 2, 5 and 3 findings at the four heads; triage reports list the dispositions.
- Decision log 318de9: the orchestrator resolved 221d69, af9b70 and 09e179 directly.
- Each triage hand-off cost between 273592 and 327547 tokens; the share spent on the no-decision comments is not separable.

## Weighing the orchestrator's shortcut

Resolving three approvals without a hand-off was a reasonable saving, but it is a write to the findings store outside the step that owns dispositions, and it left three comments without the reply the other eight received. The fix belongs in the fetch, so that the shortcut is not needed.

## Proposed action

Classify, in the fetch, a review body that states only an approval, a quality-gate status comment and a review summary whose actions are all filed as inline findings. Either drop them as noise with a counter, or store them already resolved with a reason, so they never reach triage and never gate the merge.
