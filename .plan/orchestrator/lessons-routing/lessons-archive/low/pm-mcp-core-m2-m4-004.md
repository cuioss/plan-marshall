envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:53Z

# Candidate lesson: The Sonar quality gate is evaluated only in CI, so every fix round can add issues no local build sees

- Component: plan-marshall:workflow-integration-sonar
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-012 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during the finalize phase of plan primitive-spi-and-validators (PR #18). Checked against the Sonar findings of the plan and its decision log.

## What happened

- First push (3853d09): java:S2789 (BUG, `PrimitiveRegistry.java:161`, gate-failing) and java:S1117 (`PrimitiveContractTest.java:158`).
- First fix round (3144ca4): java:S5855 (BUG, gate-failing), java:S5843 and java:S4144, all introduced by that fix, in `AsciiDocValidator.java:55` and `AsciiDocValidatorTest.java:129`.
- After the regular expression was removed: no new-code issue.

Two of the three automatic fix rounds went to Sonar regressions. The local quality gate (`verify -Ppre-commit`) was green each time.

## Verification of the wording

- Confirmed: all five rules, files and lines by the Sonar findings 814f17, b097ae, 9cd6ba, 7f094a, 750c1d (all resolved `fixed`); their timestamps (23:07:54Z for the first two, 23:40:04Z for the other three) match the two pushes.
- Confirmed: "none after the regex was removed" by decision log 318de9 (Sonar gate OK, 0 new-code issues at df4ea82).
- NOT confirmed from the decision log: that a local Sonar-equivalent check or a re-read against the rules was added by prompt in rounds 2 and 3. The task description of TASK-10 does carry rule-specific instructions (no null comparison on the Optional, no suppression), which is consistent with it.

## Proposed rule

Before a fix round is pushed, the changed lines are checked against the Sonar rules that already fired on the pull request and their neighbours (regex rules when a pattern is touched, duplicate-method rule when a test is added by copy). Where a local Sonar analysis is available, it runs as part of the pre-push gate; where it is not, the fix task carries the re-read as an explicit step rather than as a prompt addition.

## Evidence

- Sonar findings 814f17, b097ae, 9cd6ba, 7f094a, 750c1d.
- Decision log ef91c1, 318de9.
