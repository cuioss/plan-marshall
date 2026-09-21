envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=candidate-lesson
created=2026-09-07T15:17:40Z

component=pm-plugin-development:plugin-doctor
category=improvement
confidence=high
source_plan=plan-130-sweep-the-prose-the-widened-rules

# A warning-severity rule does not stay closed - the population reopened mid-run

## Context

This plan drove `test-docstring-historical-prose` from 232 findings across 111 files to **0** over its own 112-file population. The zero was verified twice — by the shipped rule itself and by an independent per-segment enumerator built for the verification deliverable — so it is a real measurement, not a self-report.

At merged `main` the whole-tree count is **3**, not 0. All three are in `test/plan-marshall/manage-tasks/test_freshness_exempt_vs_verified_discrimination.py`, added by upstream commit `ef129d6a3` (PR #1425) **while this plan was running**, and folded into the branch by the finalize rebase.

This is the second observed instance of the same shape: PLAN-080's 211-of-211 closure was falsified by an unrelated PR within two days.

## Root cause

At `warning` severity the rule reports but does not block, so a PR that introduces new findings merges freely. The backlog is closeable — this plan closed 232 of them — but it does not *stay* closed, because nothing stops the population being refilled by ordinary concurrent work. The closure and the reopening happened inside the same 22-hour window.

## Proposed action

This is direct, dated evidence for the WS-03 severity-flip decision the epic is carrying, and it argues both sides honestly:

- **For the flip.** At `error` severity, PR #1425 would have been blocked, and the tree would be at 0 today. That is precisely the enforcement the flip buys.
- **The cost of the flip.** PR #1425 is unrelated upstream work that would have been blocked on a docstring-prose rule. That is precisely what the flip costs.

The recommendation is to treat "closeable but not staying closed, twice observed" as the decisive input rather than re-litigating the backlog size. A rule whose population refills faster than sweeps can drain it is not a backlog problem.

## Evidence

- plan finding `f9f476` (insight, pending) — records the full observation with file and upstream-commit attribution.
- aspect: request_result_alignment — the plan's own 112-file population reached 0 and stayed there; the tree did not.
- The plan reported this rather than claiming a tree-wide zero it had not achieved, which is the disposition to preserve.
