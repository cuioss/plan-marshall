envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=candidate-lesson
created=2026-10-13T13:51:48Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Check required review-bot size caps before create-pr opens the PR

# Check required review-bot size caps before create-pr opens the PR

## Context

PR #1753 carried 198 changed files. `pr-decision` advised a split (201 files over its 150 limit) but the advice is advisory, so the PR was opened anyway. CodeRabbit, a required reviewer, then refused it at its hard 100-file cap, and automatic-review looped back twice before the operator chose to rebuild the change as a 5-PR stack (#1754, #1755, #1757, #1758, #1759).

## Root cause

create-pr never compares the diff against the declared size caps of the required bots (`review_completeness size-caps` already knows CodeRabbit's 100-file cap), so the incompatibility is only discovered after CI and a review round have run.

## Proposed action

Before `ci pr create`, read the required bots' size caps and, when the changed-file count exceeds a required bot's cap, stop with a prompt-required envelope offering split / accept-gap instead of opening an unreviewable PR.

## Evidence

- aspect: chat_history_analysis - CodeRabbit refused PR #1753: "198 files exceed the limit of 100"; operator chose "Split into stacked PRs"
- aspect: llm_to_script_opportunities - size-cap pre-check candidate
- aspect: plan_efficiency - 6-finalize consumed 4.1M tokens, most of it in the stack rebuild and per-part review cycles
