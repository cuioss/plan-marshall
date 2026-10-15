envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:09Z

# The triage loop-back budget during the review wait ran out twice on a review-heavy documentation PR

## What happened

During finalize of plan 39 (PR #53: module READMEs and backfilled ADRs), triage of review comments during the wait for reviews used up its loop-back budget twice. Each time the operator had to grant more budget by hand before the run could continue. The cause was that every review round from coderabbit found new factual corrections in the ADRs, so each round needed another loop-back. The changes were not going around in circles; the PR was steadily getting better.

## Rule / candidate improvement

- When the budget runs out, the escalation should report whether the loop-backs are making progress (each round fixes new, different findings) or cycling (the same findings come back). Progress is the case where granting more budget is reasonable.
- A plan whose change is mostly prose with many factual claims (ADR backfills, specifications) should expect several review rounds. Either the default budget should take this into account (for example, by sizing it from the number of ADRs or claims in the change), or the plan should ask for a larger budget in advance.
- The root cause is the same as the ADR-backfill overclaim candidate (verify claims against the code before submitting). Fixing that would also reduce how many loop-backs are needed.

## Evidence

Two operator budget grants in plan-39-module-readmes-and-adrs during the review wait in finalize.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-003.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
