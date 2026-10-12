envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:37Z

# Clamp the re-review await timeout to the Bash ceiling in the script, not in each leaf

Component: plan-marshall:workflow-integration-github (github_re_review) / phase-6-finalize automatic-review step params
Category (proposed): improvement
Confidence: high
Source: plan code-analysis-base, post-run-review retrospective (aspects llm-to-script-opportunities, chat-history-analysis)

## Context

`re_review_await_timeout_seconds` is configured to 600, which equals the 600000 ms Bash ceiling. In both re-review rounds of automatic-review, the leaf passed a smaller `--timeout` of its own choosing (570 in round 2, 540 in round 3) to keep the synchronous call inside the ceiling. This is a disclosed deviation from the configured value, and it was improvised differently each time.

## Root cause

The configured await budget and the harness Bash ceiling are set independently. No script reconciles them, so every leaf has to notice the collision and pick a margin by hand.

## Proposed action

Have `github_re_review` (or the automatic-review step-param resolver) clamp the effective await to the resolved `harness bash-timeout-ceiling` minus a fixed overhead margin, and report both `configured_timeout` and `effective_timeout` in its TOON. Alternatively, reject a configured value at or above the ceiling when the config is written.

## Evidence

- aspect: chat-history-analysis: round-2 re-review hand-back, "I passed --timeout 570 to both re-review calls instead of the configured 600"
- aspect: chat-history-analysis: round-3 re-review hand-back, "I passed --timeout 540 instead of the configured 600 for both re-review calls"
- aspect: manifest-decisions: automatic-review step_params re_review_await_timeout_seconds 600

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-014.md` from plan code-analysis-base (PLAN-36, #31)
