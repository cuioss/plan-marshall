envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=test-quality
kind=candidate-lesson
created=2026-09-23T14:46:50Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Surgical test carve correctly declines valid review-bot hardening beyond tasked scope
plan_id=module-budget-campaign-completion
source_aspects=pr-review-triage
confidence=medium

# Surgical test carve correctly declines valid review-bot hardening beyond tasked scope

## Context

PR #1593 drew 2 actionable CodeRabbit inline findings on test/_shared/_shared_harness_fixtures.py, both triaged taken_into_account with declined dispositions: tomllib derivation of EXCLUDED_DIR_NAMES plus relative_to rework, and tightening _declares_a_test to pytest-exact predicate plus new testdata positive control. Both valid as future hardening, neither a merge blocker for this test-only carve.

## Root cause

Standing surgical single-module carve (verbatim fixtures hoist) conflicts with hardening that expands scope: deriving excluded dirs from pyproject at runtime and reworking path scoping, or tightening the zero-guard predicate with extra controls, each hardens the helper beyond the tasked split. Triage held the carve boundary and recorded the hardening as future work.

## Proposed action

Keep declining out-of-carve hardening at triage with explicit valid-future-work rationale, and forward the declined-but-valid suggestions as epic candidates so the campaign can schedule them as follow-up emissions rather than expanding the surgical carve.

## Evidence

- pr-comment c5654d inline 34: EXCLUDED_DIR_NAMES tomllib derivation + relative_to fix, declined as beyond carve
- pr-comment 0b18c1 inline 55: _declares_a_test pytest-exact predicate + testdata control, declined as scope expansion
- review_body fe62a0 accepted as status summary, no actionable content
- signal: signal_automated_review_count=0 (no outstanding/remediated), 2 valid-but-declined triaged separately
