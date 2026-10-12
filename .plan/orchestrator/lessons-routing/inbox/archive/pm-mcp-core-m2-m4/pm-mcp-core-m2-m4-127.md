envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T12:40:45Z

# [HIGH][Antigravity] Final head never re-ran the project's quality gate or coverage gate; three code commits were pushed after the last gate

- Component: plan-marshall:phase-6-finalize (pre-push-quality-gate, build freshness), plan-marshall:phase-5-execute (verification steps)
- Category: bug

## What happened

- The last `verify -Ppre-commit` (OpenRewrite active) ran at 08:30Z (`maven-2026-10-12-083052.log`).
- After it came the Spotless commits (08:35Z), c47f1c0 (Sonar S1192 fix, 09:02Z), e102fbb (new tests, 11:05Z) and 8a35d93 (review fixes, 11:37Z).
- No local build ran after 11:05Z, and none of the later builds ran the pre-commit profile.
- `verify -Pcoverage` never ran. The only coverage action was a bare `jacoco:report` (default-cli) at 09:25Z, with no coverage check.
- The spec's standing constraint requires `verify`, `verify -Ppre-commit`, `verify -Pcoverage` and `verify -Pintegration-tests` green.
- CI on the final head was green (build on 25/26, integration tests, Sonar gate), so the product is not known to be broken. But the plan's own claims ("pre-commit quality gate passed", "478 tests pass") describe earlier heads.

## Why it matters

The build-freshness exemption or gate let the push through without evidence for the head that was pushed, and the PR body's test plan does not describe the merged code.

## Suggested direction

- The pre-push gate compares the last gate's HEAD with the push HEAD and refuses on a mismatch that contains source changes.
- The PR test-plan checkboxes are generated from recorded build results for the pushed SHA, not written by the agent.

- Priority: **HIGH** (operator decision 2026-10-12: Antigravity issues are filed directly as high priority)
- Platform: Antigravity — first plan of epic pm-mcp-core-m2-m4 run under it
- Plan: `plan-41-static-verifier-remaining-rules` (PLAN-41), pm-mcp-core PR #34, merge commit ebe82b3
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/` (logs/, metrics.md, execution.toon, build-results/)
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its landing analysis, verified against the archived plan and the PR
