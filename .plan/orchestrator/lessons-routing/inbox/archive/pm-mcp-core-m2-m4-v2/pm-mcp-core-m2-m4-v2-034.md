envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-18T12:23:53Z

# runbook_lane review-gate answers undecidable_read on CodeRabbit's picture-prefixed "Minor comments: N" heading

**Component:** `plan-marshall:runbook-lane` (`runbook_lane review-gate`), the one parser that counts the review body findings.

**What happened (2026-11-18, PLAN-V2-17 of the epic pm-mcp-core-m2-m4-v2, PR #496 of plan-marshall/pm-mcp-core).** The review gate answered `merge_allowed: false`, `reason: undecidable_read`, `detail: unreadable review-body section: '<picture><img src="https://storage.googleapis.com/coderabbit_public_assets/review-comment-icons-v1/amber-16.svg" width="16" height="16" align="absmiddle" alt=""></picture> Minor comments: 25'`. CI, the build, Sonar (0 new issues, gate passed) and every review thread were green or resolved; the lane handled all 29 minor and nitpick comments by reading the review body directly and stopped before the merge, because an undecidable read is a stop, never a pass. The orchestrator reproduced the answer from its own session on the same PR (`runbook_lane review-gate --pr-number 496`).

**Why it recurs.** The review body does not change between runs, so the parser answers the same on every re-run; the lane has no way to clear the gate except an operator's word. The same gate parsed the same bot's reviews of PR #487, #492, #486 and #490 of the same epic without error (totals 10, 19, 11 and 2); whether their bodies carried no icon-prefixed counted heading was not checked, so the `<picture>` wrapper CodeRabbit puts in front of the severity title is the likely trigger, not a verified one.

**Remedy to consider.** Strip a leading `<picture>...</picture>` element (and any HTML tag) before mapping a counted section title; treat an unmappable counted title as a failed parse that names the title (as now) but let the operator override it with a recorded decision instead of leaving the PR open; add a test with the amber, red and nitpick icon headings of a real CodeRabbit review.

**Evidence.** Lane message `rb-v2-17-project-onboarding-unit-001.md` § 9 Residue; the orchestrator's re-run at 2026-11-18 on head `2cfcc962` of `feature/v2-17-project-onboarding-unit`.
