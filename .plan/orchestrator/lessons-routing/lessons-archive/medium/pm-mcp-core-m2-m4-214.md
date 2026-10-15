envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:01Z

# Candidate lesson: quality-gate rewrites land after the task's own verification and are accepted blind

Source: Q-Gate finding 0efb60 (5-execute, lint-issue, warning, accepted in-run). Related: Sonar 19cd34 (separate message).

## What happened

`verify -Ppre-commit` rewrote three scenario test files (unused imports, import order, and a `throws IOException`
widened to `throws Exception`) in ScenarioDeterminismTest.java, ScenarioReplayRunnerTest.java and
ScenarioScript.java. The diff (4 insertions, 7 deletions) was reviewed as "mechanical, no behaviour change" and
accepted.

## Why it is lesson-worthy

The rewrite was not purely mechanical: the OpenRewrite step turned a narrow `throws IOException` into
`throws Exception` on a method whose body throws no checked exception, and that is exactly what Sonar java:S1130
then flagged on the PR (19cd34), costing a follow-up commit.

## Candidate rule

When the pre-commit quality gate rewrites a `throws` clause, review it as a semantic change, not a formatting one:
remove the clause when the body throws nothing checked rather than accept the widened form. More generally, a
"pre-commit rewrite accepted" disposition should not be recorded without reading each rewritten signature.

Likely owner: project-level (pm-mcp-core CLAUDE.md quality-gate guidance) or the parent POM recipe set.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-003.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
