envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T14:28:24Z

component=plan-marshall:phase-3-outline
category=improvement
source_plan=pm-mcp-core:plan-v2-98-optional-conversion-workflow

# Check the declared footprint against required review-bot caps at outline time

## Context

pm-mcp-core PLAN-V2-98 declared 113 files at outline. In 6-finalize the required review bot CodeRabbit refused PR #309 with "110 files, 10 over the limit of 100" (Sourcery also refused on diff size). The operator chose to split the model package into PR #310, which re-ran the functional review, code review, full quality gate and push - about an hour and a large share of the 1.92M finalize tokens.

## Root cause

Nothing before 6-finalize compares the declared footprint with the required review bot's file or diff cap, so a size refusal is only seen after the PR exists and every head-dependent gate has already run.

## Proposed action

At outline (or 4-plan), compare the declared affected-file count with the configured required bot's cap (`required_bots` in the automatic-review step params) and, when it exceeds it, ask the operator up front to split the deliverables into PRs under the cap or to accept the coverage gap.

## Evidence

- aspect: chat-history-analysis - operator pivot "Split the PR into diffs under the cap" in 6-finalize
- aspect: plan-efficiency - [BUDGET] error, 7.59M tokens vs 3.5M broad+tech_debt anchor; 6-finalize 1.92M
- aspect: llm-to-script-opportunities - footprint vs bot cap check proposed
