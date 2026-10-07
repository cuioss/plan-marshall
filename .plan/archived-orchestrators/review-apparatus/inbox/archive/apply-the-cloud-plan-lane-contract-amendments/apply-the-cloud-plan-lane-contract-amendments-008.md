envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:18:02Z

component=plan-marshall:phase-6-finalize
category=improvement
status=active

# Zero [VERIFY] work-log entries on a plan that ran verify at least six times

## Context

The plan's `logs/work.log` carries 412 entries. Their tag distribution is `STATUS` 56, `STEP` 41, `DISPATCH` 26, `SKILL` 16, `ARTIFACT` 13 — and `VERIFY` **zero**.

The same plan ran `pre-push-quality-gate` five times (`firing_count: 5`), ran a whole-tree `verify` after the rebase reporting 24244 tests green at `30b325984`, ran `module-tests pm-plugin-development` green at 3141 tests during execute, and ran `plugin-doctor` whole-tree. At least six verification executions, none of them visible in the tagged channel.

## Root cause

`[VERIFY] (plan-marshall:{skill}) ...` is a declared expected log pattern in the logging-gap contract, but no verification-bearing step emits it. Verification outcomes are recoverable only from `decision.log` prose and from `build-results/` files, so any consumer reading the tagged channel — including this retrospective's own `expected_vs_actual` table — concludes no verification ran.

## Proposed action

Pick one and make it true. Either emit `[VERIFY]` at each verification boundary (the gate steps, the phase-5 verification sweep, plugin-doctor), or retire `VERIFY` from the expected-pattern contract so it stops reporting a gap that no producer was ever going to fill. The current state is the worst of both: a declared category with a guaranteed zero.

## Evidence

- aspect: log_analysis — `top_tags`: STATUS 56, STEP 41, DISPATCH 26, SKILL 16, ARTIFACT 13; no VERIFY row
- aspect: logging_gap_analysis — `expected_vs_actual` VERIFY: expected_min 6, observed 0
- `status.json` — `pre-push-quality-gate` `firing_count: 5`, `display_detail: "verify green at 30b325984: compile+lint+test, 24244 tests"`
- decision.log 2026-09-04T14:06:56Z — "module-tests green at 3141 tests in 375s"
