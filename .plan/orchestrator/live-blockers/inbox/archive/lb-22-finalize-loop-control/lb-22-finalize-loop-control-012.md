envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:12Z

component=plan-marshall:phase-6-finalize
category=improvement
source_plan=lb-22-finalize-loop-control
confidence=high

# Bound the pre-submission self-review on doc-claim plans before it needs an operator close

## Context

This plan changed about 25 documents and 7 scripts. Its pre-submission self-review ran five author rounds:

| Round | Scope | Candidates | Findings |
|-------|-------|-----------|----------|
| 1 | full, 53 files | 324 | 5 |
| 2 | delta, 4 files | 61 | 4 |
| 3 | delta, 3 files | 12 | 2 |
| 4 | delta, 2 files | 6 | 0 |
| 4, closing pass | full, 53 files | 324 | 7 |

Every finding was a prose or contract claim (a sentence wider than the code, "only", "never", a stale docstring). All were low severity. Most later findings were unswept siblings of a claim an earlier round had removed; one was prose a fix round had itself written. The closing full pass found more than the first full pass had. With four of five rounds spent, the operator chose "fix the 7 and stop reviewing" and closed the step with the operator-close verb this plan had just built; the last fix commit shipped unreviewed by this step.

No author round completed the step's own setup. Step 2a requires reading every contract source and every schema-bearing file in full; each round reported reading 3 to 8 of roughly 220 files and said so.

## Root cause

- The check has no stopping rule other than "a full pass finds nothing", and on a large prose surface a more careful full pass always finds something.
- The class sweep is bounded to the surfaced candidates of one round, so siblings of a removed claim in files outside a delta wait for the closing full pass, where they arrive together.
- Step 2a's read-everything instruction is not achievable at this surface size, so each round's coverage is whatever the author chose.

## Proposed action

- After a class is first found, sweep that class over the full surface once (not only the delta), so its siblings are fixed in one round.
- Give the step a severity floor or a convergence rule for prose-only rounds: for example, a second full pass that returns only low-severity prose findings files them and closes, without a further loop-back.
- Replace "read every file in full" in Step 2a with a bounded instruction the author can actually meet and report against.

## Evidence

- aspect: chat_history_analysis - five author hand-backs with the figures above; verifier answer after round 1: "may_close: no ... left ~200 files unread".
- status record: `pre-submission-self-review` prior firings `loop_back x4, done, done`; final facts `may_close: operator_override`, `acceptance: operator_override`.
- related: lesson `2026-10-05-17-003` in the corpus (self-review self-seeds on doc-claim plans) describes the same family; lessons-housekeeping kept it because "the narrow-instead-of-reword rule is not codified".
