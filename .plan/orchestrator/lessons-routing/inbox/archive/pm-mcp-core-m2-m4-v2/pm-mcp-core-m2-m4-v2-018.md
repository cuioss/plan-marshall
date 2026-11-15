envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:10Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Scope review re-fires to the delta when a HEAD advance leaves reviewed files intact

# Scope review re-fires to the delta when a HEAD advance leaves reviewed files intact

## Context

Four HEAD advances during finalize (wording fix 4bab2358, repeated-counter fix 53413611, triage fix bca5ff23, branch-cleanup rebase bf9d510a) each re-fired functional-review and code-review as full rounds because `verdict_inputs` were undeclared. functional-review fired 6 times and code-review 4 times. After the rebase, 25 of the 26 plan files were byte-identical to the closed round (only spec 03 changed, through upstream #391). 6-finalize consumed 4.55M of the plan's 7.55M tokens (60%); the plan crossed the multi_module + bug_fix error anchor (2.0M) by 3.8x.

## Root cause

With `verdict_inputs` undeclared, the head-dependent review steps cannot tell a delta that touches reviewed files from one that does not, so every advance is a full re-review.

## Proposed action

Declare the review steps' verdict inputs (the plan footprint) so a HEAD advance whose diff against the closed head misses them, or touches only a few, runs a delta round; keep a full round for a delta that touches production code broadly.

## Evidence

- aspect: plan_efficiency — max_phase_token_share 0.60, [BUDGET] error at 2.0M (7.5M observed)
- aspect: chat_history_analysis — fifth functional-review round: "git diff bca5ff23 HEAD --stat shows 9 files changed, none of them in the plan's footprint except spec 03"
- decision.log 8df599, 026e2b, f9f9e3 — "verdict_inputs undeclared, so both re-fire as full rounds"
- plan: plan-v2-132-coverage-parser-hardening
