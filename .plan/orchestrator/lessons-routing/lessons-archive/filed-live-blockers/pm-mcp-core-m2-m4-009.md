envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:58Z

# Candidate lesson: A deliverable in a sibling repository cannot be closed by the plan's phases

- Component: plan-marshall:phase-6-finalize
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-017 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during plan primitive-spi-and-validators. Checked against the decision log of the plan.

## What happened

Deliverable 6 was the documentation pull request in the sibling checkout `plan-marshall-documentation`. Its paths lie outside this repository, so the tooling that tracks which files a plan touches does not reach them. Its pull request must name the code pull request, which exists only once the finalize phase has created it. The plan's phases therefore could commit the documentation change but neither push it nor open its pull request. That was done by a separate hand-off after the operator approved it.

## State left behind

Documentation pull request plan-marshall/plan-marshall-documentation #20 is OPEN and NOT merged. It names pm-mcp-core #18. Not read there: PM-WATCH-TOOL-6, PM-WATCH-DISP-18, PM-WATCH-STORE-1. Its link check and its rendering were not looked at.

## Verification of the wording

- Confirmed: deliverable 6 added as a manual deliverable in the sibling checkout on outline re-entry (decision log aaa3a4).
- Confirmed: "all paths lie outside this repository and its inventory, so module attribution and the content sweeps do not reach them" (4c0e80).
- Confirmed: commit f0cb9bc on the documentation branch, "not pushed, no pull request", during execute (4f5a2e).
- Confirmed: pull request #20 opened by operator decision after the merge, commits f0cb9bc + 013b6ab, not merged, with the unread items as listed above (72429e).

## Proposed rule

A plan that owns a change in a second repository states at outline time who opens that pull request and when: after `create-pr` of the code repository, as a named finalize step with the code pull request number as its input. Until such a step exists, the landing of the plan lists the second pull request as open work, not as done.

## Evidence

- Decision log aaa3a4, 4c0e80, 4f5a2e, 72429e.
