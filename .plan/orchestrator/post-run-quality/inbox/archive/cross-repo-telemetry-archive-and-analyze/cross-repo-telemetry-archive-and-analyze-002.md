envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:21:25Z

component=plan-marshall:phase-6-finalize
category=improvement

# Check required-bot PR size caps before create-pr and plan a dependency-aware split

## Context

PR #1691 carried 151 files. Required reviewer CodeRabbit refused it on its 100-file cap (optional Sourcery refused on its 150,000-character cap). The refusal surfaced only after push, create-pr and ci-verify had run. The operator chose a split: #1691 was closed, part 1 (#1692) was cut as a cherry-pick of the test-mirror deletion, and #1692 then needed two fix commits because the still-registered era-stamp step's verdict_inputs and an import kept two mirror files (test_audit_check_era_model.py, _audit_fixtures.py) alive. #1692 merged with 74 deletions; part 2 (#1694) carried 78 files.

## Root cause

Nothing compares the planned footprint against the required bots' published size caps before a PR is opened, and the split was cut by file group rather than by dependency, so files still referenced from the other part were cut into the first.

## Proposed action

Before create-pr (or at phase-4-plan, where the footprint is already known), compare the in-repo changed-file count and diff size against each required bot's cap; when exceeded, propose the split up front and validate the cut by checking that no path in part 1 is still referenced (registered step verdict_inputs, imports, fixtures) by code that only changes in part 2.

## Evidence

- aspect: chat_history_analysis - automatic-review escalate_ask refusal_structural, coderabbit cap 100, PR 151 files; operator answer "Split into 2 PRs"
- decision.log 18:50:51Z - split recorded: #1691 closed, #1692 cherry-pick of 9706647de
- git: #1692 (5ec134b0f) deleted 74 files; the plan's mirror deletion commit deleted 76; the 2 left behind shipped in #1694
- status.json: create-pr firing_count 2, ci-verify firing_count 3
